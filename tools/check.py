#! /usr/bin/env python

"""
Validate Software Carpentry lessons
according to the Markdown template specification described here:
http://software-carpentry.org/blog/2014/10/new-lesson-template-v2.html

Validates the presence of headings, as well as specific sub-nodes.
Contains validators for several kinds of template.

Call at command line with flag -h to see options and usage instructions.
"""
from __future__ import print_function

import argparse
import collections
import glob
import hashlib
import logging
import os
import re
import sys

import json
import pypandoc
import pandocfilters

import validation_helpers as vh
import filters.common as fc

class MarkdownValidator(object):
    """Base class for Markdown validation

    Contains basic validation skeleton to be extended for specific page types
    """
    EXPECTED_HEADINGS = []  # List of strings containing expected heading text

    # Callout boxes (blockquote items) have special rules.
    # Dict of tuples for each callout type: {style: (title, min, max)}
    EXPECTED_CALLOUTS = {}

    WARN_ON_EXTRA_HEADINGS = True  # Warn when other headings are present?

    # Validate YAML doc headers: dict of {header text: validation_func}
    EXPECTED_DOC_HEADERS = {}  # Rows in header section (first few lines of document).

    def __init__(self, filename=None, markdown=None):
        """Perform validation on a Markdown document.

        Validator accepts either the path to a file containing Markdown,
        OR a valid Markdown string. The latter is useful for unit testing."""
        self.filename = filename

        if filename:
            # Expect Markdown files to be in same directory as the input file
            self.markdown_dir = os.path.dirname(filename)
            self.lesson_dir = self.markdown_dir
            with open(filename, 'rU') as f:
                self.markdown = f.read()
        else:
            # Look for linked content in ../pages (relative to this file)
            self.lesson_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), os.pardir))

            self.markdown_dir = self.lesson_dir
            self.markdown = markdown

        self.header, self.ast = self._parse_markdown()
        self.anchors = []

        def get_anchors(key, val, format, meta):
            if key == "Header":
                self.anchors.append(val[1][0])
            if key == "DefinitionList":
                for definition in val:
                    self.anchors.append(fc.text2fragment_identifier(pandocfilters.stringify(definition[0])))

        pandocfilters.walk(self.ast, get_anchors, "", {})

    def _parse_markdown(self):
        ast = json.loads(pypandoc.convert(''.join(self.markdown),
                                          'json',
                                          'markdown'))
        return ast[0]["unMeta"], ast[1]

    def _validate_one_element_from_header(self, key):
        """Validate a single row of the document header section"""
        res = True

        if key not in self.EXPECTED_DOC_HEADERS:
            logging.warning(
                "In {0} YAML header: "
                "Unrecognized label '{1}'".format(
                    self.filename, key))
            res = False
        else:
            # FIXME: This depends on
            # https://github.com/jgm/pandocfilters/pull/14
            node = [self.header[key]]
            if not self.EXPECTED_DOC_HEADERS[key](pandocfilters.stringify(node)):
                logging.error(
                    "In {0} YAML header: "
                    "label '{1}' "
                    "does not follow expected format".format(self.filename, key))
                res = False

        return res

    def _validate_header(self):
        """Validate YAML header.

        Verify that the header section at top of document
        is bracketed by two horizontal rules."""
        res = True

        if len(self.header) == 0:
            logging.error(
                "In {0}: "
                "Document must include YAML header".format(self.filename))
            res = False
        else:
            for key in self.header:
                res = res and self._validate_one_element_from_header(key)

            # TODO Labeled YAML should match expected format

            # TODO Must have all expected header lines, and no others.

        return res

    # TODO Split this function by creating _validade_one_heading.
    def _validate_headings(self):
        """Validate headings present at the document.

        Pass only if the headings in the document contains the specified
        ones with the expected contents."""

        res = True
        headings = []

        # We only have to check heading at the first level of AST.
        for node in self.ast:
            if node['t'] == "Header":
                headings.append(node)

                # All headings should be exactly level 2
                if node['c'][0] != 2:
                    logging.error(
                        "In {0}: "
                        "Heading '{1}' should be level 2".format(
                            self.filename, pandocfilters.stringify(node)))
                    res = False

        heading_labels = [pandocfilters.stringify(node) for node in headings]

        # Check for missing heading
        missing_headings = [expected_heading for expected_heading in self.EXPECTED_HEADINGS
                if expected_heading not in heading_labels]
        for heading in missing_headings:
            logging.error(
                "In {0}: "
                "Document is missing expected heading: {1}".format(
                    self.filename, heading))
            res = False 
        
        # Check for extra headings
        if self.WARN_ON_EXTRA_HEADINGS:
            extra_headings = [found_heading for found_heading in heading_labels
                    if found_heading not in self.EXPECTED_HEADINGS]
            for heading in extra_headings:
                logging.error(
                    "In {0}: "
                    "Document contains heading "
                    "not specified in the template: {1}".format(
                        self.filename, heading))
                res = False

        # FIXME Check that the subset of headings
        # in the template spec matches order in the document
        if len(headings) == len(self.EXPECTED_HEADINGS):
            for i, node in enumerate(headings):
                if pandocfilters.stringify(node) != self.EXPECTED_HEADINGS[i]:
                    logging.error(
                        "In {0}: "
                        "Heading '{1}' should be {2}".format(
                            self.filename,
                            pandocfilters.stringify(node),
                            self.EXPECTED_HEADINGS[i]))
                    res = False
        else:
            logging.error(
                "In {0}: "
                "Incorrect number of heading".format(
                    self.filename))
            res = False

        return res

    def _validate_one_callout(self, callout):
        """
        Logic to validate a single callout box (defined as a blockquoted
        section that starts with a heading). Checks that:

        * First child of callout box should be a lvl 2 header with
          known title & CSS style
        * Callout box must have at least one child after the heading

        An additional test is done in another function:
        * Checks # times callout style appears in document, minc <= n <= maxc
        """
        res = True

        if len(callout['c']) == 1:
            logging.error(
                "In {0}: "
                "Box '{1}' should not be empty.".format(
                    self.filename,
                    pandocfilters.stringify(callout['c'][0])))
            res = False

        return res

    def _validate_boxes(self):
        """Validate boxes present at the document.

        Pass only if the headings in the document contains the specified
        ones with the expected contents."""

        res = True
        boxes = []

        # We only need to check boxes at the first level of AST.
        for node in self.ast:
            if (node['t'] == "BlockQuote" and
                    len(node['c']) > 0 and
                    node['c'][0]['t'] == "Header"):
                boxes.append(node)

        for box in boxes:
            box_type = box['c'][0]['c'][1][1]
            if len(box_type) > 0:
                box_type = box_type[0]
            else:
                box_type = None

            if box_type == "objectives":
                # TODO Write function to validate objectives
                pass
            elif box_type == "callout":
                res = res and self._validate_one_callout(box)
            elif box_type == "challenge":
                # TODO Write function to validate objectives
                pass

        return res

    def _validate_one_anchor(self, file_path, anchor):
        """Validate a single anchor."""
        dest = MarkdownValidator(file_path)
        return anchor in dest.anchors

    def _validate_one_link(self, address, link_text):
        """Validate a single link."""
        # Not need to validate links to third party sites.
        if not re.match(r"^((https?|ftp)://)", address, re.IGNORECASE):
            dest = address.split("#")
            if len(dest) > 1:
                anchor = dest[1]
            else:
                anchor = None
            dest = dest[0] or self.filename
            dest_path = os.path.join(self.lesson_dir, dest)

            # If HTML file need to check for Markdown file.
            if re.search(r"\.(html?)$", dest_path, re.IGNORECASE):
                dest_path = dest_path.replace(".html", ".md")

                if not os.path.isfile(dest_path):
                    logging.error(
                        "In {0}: "
                        "The document links to {1}, but could not find "
                        "the expected Markdown file {2}".format(
                            self.filename, address, dest_path))
                    return False
                elif anchor:
                    if not anchor in MarkdownValidator(dest_path).anchors:
                        logging.error(
                            "In {0}: "
                            "The document links to {1}, but could not find "
                            "the anchor {2} in {3}".format(
                                self.filename, address, anchor, dest_path))
                        return False
            else:
                if not os.path.isfile(dest_path):
                    logging.error(
                        "In {0}: "
                        "Could not find the linked asset file "
                        "{1}. If this is a URL, it must be "
                        "prefixed with http(s):// or ftp://.".format(
                            self.filename, dest_path))
                    return False

        return True

    def _validate_links(self):
        """Validate links.

        Verify that all the links in the document are valid."""
        res = True
        links = []  # List of ('text', 'address')

        def get_links(key, val, format, meta):
            if key == "Link":
                links.append(
                    (pandocfilters.stringify(val[0]),
                     val[1][0]))

        pandocfilters.walk(self.ast, get_links, "", {})

        for link in links:
            res = res and self._validate_one_link(link[1], link[0])

        return res

    def _run_tests(self):
        """
        Let user override the list of tests to be performed.

        Error trapping is handled by the validate() wrapper method.
        """
        tests = [self._validate_header(),
                 self._validate_headings(),
                 self._validate_boxes(),
                 self._validate_links()]

        return all(tests)

    def validate(self):
        """Perform all required validations. Wrap in exception handler"""
        try:
            return self._run_tests()
        except IndexError:
            logging.error("Document is missing critical sections")
            return False


class IndexPageValidator(MarkdownValidator):
    """Validate the contents of the homepage (index.md)"""
    EXPECTED_HEADINGS = ['Topics',
                'Other Resources']

    EXPECTED_DOC_HEADERS = {'layout': vh.is_str,
                            'title': vh.is_str}

    EXPECTED_CALLOUTS = {'prereq': ("Prerequisites", 1, 1)}

    # TODO Improve the following function
    def _validate_intro_section(self):
        """Validate the intro section.

        It must be a paragraph, followed by blockquoted list of prereqs."""
        if self.ast[0] and self.ast[0]['t'] != "Para":
            logging.warning(
                "In {0}: "
                "The first element must be a paragraph.".format(
                    self.filename))
            return False

        if self.ast[1] and self.ast[1]['t'] != "BlockQuote":
            logging.warning(
                "In {0}: "
                "The second element must be a blockquote.".format(
                    self.filename))
            return False
        else:
            blockquote = self.ast[1]['c']
            if blockquote[0] and blockquote[0]['t'] != "Header":
                logging.warning(
                    "In {0}: "
                    "The first element at the blockquote must be a header.".format(
                        self.filename))
                return False

            if blockquote[1] and blockquote[1]['t'] != "BulletList":
                logging.warning(
                    "In {0}: "
                    "The second element at the blockquote must be a header.".format(
                        self.filename))
                return False

        return true

    def _run_tests(self):
        parent_tests = super(IndexPageValidator, self)._run_tests()
        tests = [self._validate_intro_section()]
        return all(tests) and parent_tests


class TopicPageValidator(MarkdownValidator):
    """Validate the Markdown contents of a topic page, eg 01-topicname.md"""
    EXPECTED_DOC_HEADERS = {"layout": vh.is_str,
                            "title": vh.is_str,
                            "subtitle": vh.is_str,
                            "minutes": vh.is_numeric}

    EXPECTED_CALLOUTS = {"objectives": ("Learning Objectives", 1, 1),
                         "callout": (None, 0, None),
                         "challenge": (None, 0, None)}

    # TODO Improve the following function
    def _validate_learning_objective(self):
        """Validate learning objective."""
        res = True
        if self.ast[0] and self.ast[0]['t'] != "BlockQuote":
            logging.warning(
                "In {0}: "
                "The first element must be a blockquote.".format(
                    self.filename))
            res = False
        else:
            blockquote = self.ast[0]['c']
            if blockquote[0] and blockquote[0]['t'] != "Header":
                logging.warning(
                    "In {0}: "
                    "The first element at the blockquote must be Header.".format(
                        self.filename))
                res = False

            if blockquote[1] and blockquote[1]['t'] != "BulletList":
                logging.warning(
                    "In {0}: "
                    "The second element at the blockquote must be a list.".format(
                        self.filename))
                res = False

        return res

    def _validate_has_no_headings(self):
        """Check headings

        The top-level document has no headings indicating subtopics.
        The only valid subheadings are nested in blockquote elements"""
        res = True

        for node in self.ast:
            if node['t'] == "Header":
                logging.warning(
                    "In {0}: "
                    "Heading are not allowed. Consider breaking this lesson at \"{1}\".".format(
                        self.filename, pandocfilters.stringify(node['c'])))
                res = False

        return res

    def _run_tests(self):
        parent_tests = super(TopicPageValidator, self)._run_tests()
        tests = [self._validate_learning_objective(),
                 self._validate_has_no_headings()]
        return all(tests) and parent_tests

class MotivationPageValidator(MarkdownValidator):
    """Validate motivation.md"""
    WARN_ON_EXTRA_HEADINGS = False

    EXPECTED_DOC_HEADERS = {"layout": vh.is_str,
                            "title": vh.is_str,
                            "subtitle": vh.is_str}


class ReferencePageValidator(MarkdownValidator):
    """Validate reference.md"""
    EXPECTED_HEADINGS = ["Glossary"]
    WARN_ON_EXTRA_HEADINGS = False

    EXPECTED_DOC_HEADERS = {"layout": vh.is_str,
                            "title": vh.is_str,
                            "subtitle": vh.is_str}

    def _validate_glossary(self):
        """Validate glossary entry

        Glossary entry must be formatted in conformance with Pandoc's
        ```definition_lists``` extension."""
        res = True
        glossary = []

        for node in self.ast:
            if node['t'] == "DefinitionList":
                glossary.append(node)

        if len(glossary) == 0:
            logging.error(
                "In {0}:"
                "Missing glossary entry.".format(
                    self.filename))
            res = False

        return res

    def _run_tests(self):
        tests = [self._validate_glossary()]
        parent_tests = super(ReferencePageValidator, self)._run_tests()
        return all(tests) and parent_tests


class InstructorPageValidator(MarkdownValidator):
    """Simple validator for Instructor's Guide- instructors.md"""
    EXPECTED_HEADINGS = ["Legend", "Overall"]
    WARN_ON_EXTRA_HEADINGS = False

    EXPECTED_DOC_HEADERS = {"layout": vh.is_str,
                            "title": vh.is_str,
                            "subtitle": vh.is_str}


class LicensePageValidator(MarkdownValidator):
    """Validate LICENSE.md: user should not edit this file"""
    def _run_tests(self):
        """Skip the base tests; just check md5 hash"""
        expected_hash = 'cd5742b6596a1f2f35c602ad43fa24b2'
        m = hashlib.md5()
        try:
            m.update(self.markdown)
        except TypeError:
            # Workaround for hashing in python3
            m.update(self.markdown.encode('utf-8'))

        if m.hexdigest() == expected_hash:
            return True
        else:
            logging.error("The provided license file should not be modified.")
            return False


class DiscussionPageValidator(MarkdownValidator):
    """
    Validate the discussion page (discussion.md).
    Most of the content is free-form.
    """
    WARN_ON_EXTRA_HEADINGS = False
    EXPECTED_DOC_HEADERS = {"layout": vh.is_str,
                            "title": vh.is_str,
                            "subtitle": vh.is_str}


# Associate lesson template names with validators. This list used by CLI.
#   Dict of {name: (Validator, filename_pattern)}
LESSON_TEMPLATES = {"index": (IndexPageValidator, "^index"),
                    "topic": (TopicPageValidator, "^[0-9]{2}-.*"),
                    "motivation": (MotivationPageValidator, "^motivation"),
                    "reference": (ReferencePageValidator, "^reference"),
                    "instructor": (InstructorPageValidator, "^instructors"),
                    "license": (LicensePageValidator, "^LICENSE"),
                    "discussion": (DiscussionPageValidator, "^discussion")}

# List of files in the lesson directory that should not be validated at all
SKIP_FILES = ("DESIGN.md", "FAQ.md", "LAYOUT.md", "README.md")


def identify_template(filepath):
    """Identify template

    Given the path to a single file,
    identify the appropriate template to use"""
    for template_name, (validator, pattern) in LESSON_TEMPLATES.items():
        if re.search(pattern, os.path.basename(filepath)):
            return template_name

    return None


def validate_single(filepath, template=None):
    """Validate a single Markdown file based on a specified template"""
    if os.path.basename(filepath) in SKIP_FILES:
        # Silently pass certain non-lesson files without validating them
        return True

    template = template or identify_template(filepath)
    if template is None:
        logging.error(
            "Validation failed for {0}: "
            "Could not automatically identify correct template.".format(
                filepath))
        return False

    logging.debug(
        "Beginning validation of {0} using template {1}".format(
            filepath, template))
    validator = LESSON_TEMPLATES[template][0]
    validate_file = validator(filepath)

    res = validate_file.validate()
    if res is True:
        logging.debug("File {0} successfully passed validation".format(
            filepath))
    else:
        logging.debug("File {0} failed validation: "
                      "see error log for details".format(filepath))

    return res


def validate_folder(path, template=None):
    """Validate an entire folder of files"""
    search_str = os.path.join(path, "*.md")  # Find files based on extension
    filename_list = glob.glob(search_str)

    if not filename_list:
        logging.error(
            "No Markdown files were found "
            "in specified directory {0}".format(path))
        return False

    all_valid = True
    for fn in filename_list:
        res = validate_single(fn, template=template)
        all_valid = all_valid and res
    return all_valid


def start_logging(level=logging.INFO):
    """Initialize logging and print messages to console."""
    logging.basicConfig(stream=sys.stdout, level=level)


def command_line():
    """Handle arguments passed in via the command line"""
    parser = argparse.ArgumentParser()
    parser.add_argument("file_or_path",
                        nargs="*",
                        default=[os.getcwd()],
                        help="The individual pathname")

    parser.add_argument('-t', '--template',
                        choices=LESSON_TEMPLATES.keys(),
                        help="The type of template to apply to all file(s). "
                             "If not specified, will auto-identify template.")

    parser.add_argument('-d', '--debug',
                        action='store_true',
                        help="Enable debug information.")

    return parser.parse_args()


def check_required_files(dir_to_validate):
    """Check if required files exists."""
    REQUIRED_FILES = ["01-*.md",
                      "discussion.md",
                      "index.md",
                      "instructors.md",
                      "LICENSE.md",
                      "motivation.md",
                      "README.md",
                      "reference.md"]
    valid = True

    for required in REQUIRED_FILES:
        req_fn = os.path.join(dir_to_validate, required)
        if not glob.glob(req_fn):
            logging.error(
                "Missing file {0}.".format(required))
            valid = False

    return valid


def get_files_to_validate(file_or_path):
    """Generate list of files to validate."""
    files_to_validate = []
    dirs_to_validate = []

    for fn in file_or_path:
        if os.path.isdir(fn):
            search_str = os.path.join(fn, "*.md")
            files_to_validate.extend(glob.glob(search_str))
            dirs_to_validate.append(fn)
        elif os.path.isfile(fn):
            files_to_validate.append(fn)
        else:
            logging.error(
                "The specified file or folder {0} does not exist; "
                "could not perform validation".format(fn))

    return files_to_validate, dirs_to_validate


def main(parsed_args_obj):
    if parsed_args_obj.debug:
        log_level = "DEBUG"
    else:
        log_level = "WARNING"
    start_logging(log_level)

    template = parsed_args_obj.template

    all_valid = True

    files_to_validate, dirs_to_validate = get_files_to_validate(
        parsed_args_obj.file_or_path)

    # If user ask to validate only one file don't check for required files.
    for d in dirs_to_validate:
        all_valid = all_valid and check_required_files(d)

    for fn in files_to_validate:
        res = validate_single(fn, template=template)

        all_valid = all_valid and res

    if all_valid is True:
        logging.debug("All Markdown files successfully passed validation.")
        sys.exit(0)
    else:
        logging.warning(
            "Some errors were encountered during validation. "
            "See log for details.")
        sys.exit(1)


if __name__ == "__main__":
    parsed_args = command_line()
    main(parsed_args)
