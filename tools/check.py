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
import glob
import hashlib
import itertools
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
    EXPECTED_BOXES = {}

    WARN_ON_EXTRA_HEADINGS = True  # Warn when other headings are present?

    # Validate YAML doc header: dict of {header text: validation_func}
    EXPECTED_YAML_HEADER = {}

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

        self.ast = vh.PandocAstHelper(self.markdown)

    def _validate_no_fixme(self):
        """Validate that the file contains no lines marked 'FIXME'
        This will be based on the raw markdown, not the ast"""
        valid = True
        for i, line in enumerate(self.markdown.splitlines()):
            if re.search("FIXME", line, re.IGNORECASE):
                logging.error(
                    "In {0}: "
                    "Line {1} contains FIXME, indicating "
                    "work in progress".format(self.filename, i+1))
                valid = False
        return valid

    def _validate_one_element_from_header(self, key):
        """Validate a single row of the document header section"""
        res = True

        if key not in self.EXPECTED_YAML_HEADER:
            logging.warning(
                "In {0} YAML header: "
                "Unrecognized label '{1}'".format(
                    self.filename, key))
            res = False
        else:
            # FIXME: This depends on
            # https://github.com/jgm/pandocfilters/pull/14
            node = [self.ast.header[key]]
            if not self.EXPECTED_YAML_HEADER[key](vh.ast_to_string(node)):
                logging.error(
                    "In {0} YAML header: "
                    "label '{1}' "
                    "does not follow expected format".format(self.filename, key))
                res = False

        return res

    def _validate_header(self):
        """Validate YAML header."""
        res = True

        if len(self.ast.header) == 0:
            logging.error(
                "In {0}: "
                "Document must include YAML header".format(self.filename))
            res = False
        else:
            # Check if YAML keys and values are valide
            for key in self.ast.header:
                res = res and self._validate_one_element_from_header(key)

            # Must have all expected header lines, and no others.
            for expected, occurred in itertools.zip_longest(
                    sorted(self.EXPECTED_YAML_HEADER),
                    sorted(self.ast.header)):
                if expected is None:
                    logging.error(
                        "In {0}: "
                        "Extra key {1} in YAML header".format(self.filename,
                            occurred))
                    res = False
                elif occurred is None:
                    logging.error(
                        "In {0}: "
                        "Missing key {1} in YAML header".format(self.filename,
                            expected))
                    res = False
                elif expected != occurred:
                    logging.error(
                        "In {0}: "
                        "Key {1} in YAML header should be {2}".format(self.filename,
                            occurred, expected))
                    res = False

        return res

    # TODO Split this function by creating _validade_one_heading.
    def _validate_one_heading(self, heading):
        """Validade one heading."""
        res = True

        level, title = heading

        # Headings should be exactly level 2
        if level != 2:
            logging.error(
                "In {0}: "
                "Heading '{1}' should be level 2".format(
                    self.filename, title))
            res = False

        return res

    def _validate_headings_order(self):
        res = True

        headings = [title for level, title in self.ast.get_headings() if level == 2]

        for expected, occurred in itertools.zip_longest(self.EXPECTED_HEADINGS,
                headings):
            if expected is None:
                logging.error(
                    "In {0}: "
                    "Extra heading {1}".format(self.filename,
                        occurred))
                res = False
            elif occurred is None:
                logging.error(
                    "In {0}: "
                    "Missing heading {1}".format(self.filename,
                        expected))
                res = False
            elif expected != occurred:
                logging.error(
                    "In {0}: "
                    "Heading {1} should be {2}".format(self.filename,
                        occurred, expected))
                res = False

        return res

    def _validate_headings(self):
        """Validate headings present at the document.

        Pass only if the headings in the document contains the specified
        ones with the expected contents."""
        res = True
        headings = self.ast.get_headings()

        for heading in headings:
            res = res and self._validate_one_heading(heading)

        heading_titles = [title for (level, title) in headings]

        # Check for missing heading
        missing_headings = [expected_heading for expected_heading in self.EXPECTED_HEADINGS
                if expected_heading not in heading_titles]
        for heading in missing_headings:
            logging.error(
                "In {0}: "
                "Document is missing expected heading: {1}".format(
                    self.filename, heading))
            res = False

        # Check for extra headings
        if self.WARN_ON_EXTRA_HEADINGS:
            extra_headings = [found_heading for found_heading in heading_titles
                    if found_heading not in self.EXPECTED_HEADINGS]
            for heading in extra_headings:
                logging.error(
                    "In {0}: "
                    "Document contains heading "
                    "not specified in the template: {1}".format(
                        self.filename, heading))
                res = False

            # TODO Check that the subset of headings
            # in the template spec matches order in the document
            res = res and self._validate_headings_order()

        return res

    def _is_box_nonempty(self, ast_node):
        """Logic to check if box is empty."""
        if len(ast_node['c']) == 1:
            logging.error(
                "In {0}: "
                "Box '{1}' should not be empty.".format(
                    self.filename,
                    vh.ast_to_string(ast_node['c'][0])))
            return False
        else:
            return True

    def _is_callout_box(self, ast_node):
        """Logic to validate a single callout box
        (defined as a blockquoted section
        that starts with a heading). Check that:

        *   First child of box should a level 2 heading
            with CSS style
        *   Box must at least a second element
        """
        res = True

        res = res and self._is_box_nonempty(ast_node)

        return res

    def _is_challenge_box(self, ast_node):
        """Logic to validate a single challenge box
        (defined as a blockquoted section
        that starts with a heading). Check that:

        *   First child of box should a level 2 heading
            with CSS style
        *   Box must at least a second element
        """
        res = True

        res = res and self._is_box_nonempty(ast_node)

        return res

    def _is_objectives_box(self, ast_node):
        """Logic to validate a single objective box
        (defined as a blockquoted section
        that starts with a heading). Check that:

        *   First child of box should a level 2 heading
            with CSS style
        *   Box must have only one paragraph.
        """
        res = True

        res = res and self._is_box_nonempty(ast_node)

        if ast_node['c'][1]['t'] != "BulletList":
            logging.error(
                "In {0}: "
                "Box '{1}' should has a list as second element.".format(
                    self.filename,
                    vh.ast_to_string(ast_node['c'][0])))
            res = False

        if len(ast_node['c']) > 2:
            logging.error(
                "In {0}: "
                "Box '{1}' should has only one heading and one list.".format(
                    self.filename,
                    vh.ast_to_string(ast_node['c'][0])))
            res = False

        return res

    def _is_prereq_box(self, ast_node):
        """Logic to validate a single prereq box
        (defined as a blockquoted section
        that starts with a heading). Check that:

        *   First child of box should a level 2 heading
            with CSS style
        *   Box must at least a second element
        """
        res = True

        # TODO This need improvements to support internationalization
        if vh.ast_to_string(ast_node['c'][0]) != "Prerequisites":
            logging.error(
                "In {0}: "
                "Title of box '{1}' should be Prerequisites.".format(
                    self.filename,
                    vh.ast_to_string(ast_node['c'][0])))
            res = False

        res = res and self._is_box_nonempty(ast_node)

        if ast_node['c'][1]['t'] != "Para":
            logging.error(
                "In {0}: "
                "Box '{1}' should has a paragraph as second element.".format(
                    self.filename,
                    vh.ast_to_string(ast_node['c'][0])))
            res = False

        if len(ast_node['c']) > 2:
            logging.error(
                "In {0}: "
                "Box '{1}' should has only one heading and one list.".format(
                    self.filename,
                    vh.ast_to_string(ast_node['c'][0])))
            res = False

        return res

    def _validate_boxes(self):
        """Validate boxes present at the document.

        Pass only if the headings in the document contains the specified
        ones with the expected contents."""

        res = True
        boxes_type_and_functions = [('callout', self._is_callout_box),
                                    ('challenge', self._is_callout_box),
                                    ('objectives', self._is_objectives_box),
                                    ('prereq', self._is_prereq_box)]

        boxes = self.ast.get_boxes()
        boxes_counters = {}

        for box in boxes:
            if vh.get_box_level(box) != 2:
                logging.error(
                    "In {0}: "
                    "The title of box {1} must be of level 2.".format(
                        self.filename,
                        vh.get_box_title(box)))
                res = res and False

            box_type = vh.get_box_type(box)
            if box_type not in boxes_counters:
                boxes_counters[box_type] = 0

            box_is_know = False
            for box_type_, box_function_ in boxes_type_and_functions:
                if box_type == box_type_:
                    box_is_know = True
                    if box_function_(box):
                        boxes_counters[box_type] += 1
                    else:
                        res = False
            if not box_is_know:
                logging.error(
                    "In {0}: "
                    "Box {1} of unknown type.".format(
                        self.filename,
                        vh.get_box_title(box)))
                res = res and False

        for expected_box_type in self.EXPECTED_BOXES:
            _, min_, max_ = self.EXPECTED_BOXES[expected_box_type]

            if expected_box_type not in boxes_counters:
                if min_ > 0:
                    logging.error(
                        "In {0}: "
                        "Missing box {1}.".format(
                            self.filename,
                            expected_box_type))
                    res = False
            elif (min_ > boxes_counters[expected_box_type]
                    or max_ < boxes_counters[expected_box_type]):
                logging.error(
                    "In {0}: "
                    "Should be at least {1} "
                    "and no more than {2} box {3}.".format(
                        self.filename, min_, max_,
                        expected_box_type))
                res = False

        return res

    def _validate_one_anchor(self, file_path, anchor):
        """Validate a single anchor."""
        dest = MarkdownValidator(file_path)
        return anchor in dest.ast.anchors

    def _validate_one_link(self, address, link_text):
        """Validate a single link."""
        # Not need to validate links to third party sites.
        if (not re.match(r"^((https?|ftp)://)", address, re.IGNORECASE)
                and not re.match(r"^mailto:", address)):
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
                    if not anchor in MarkdownValidator(dest_path).ast.anchors:
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
            if key in ("Link", "Image"):
                links.append(
                    (vh.ast_to_string(val[0]),
                     val[1][0]))

        pandocfilters.walk(self.ast.body, get_links, "", {})

        for link in links:
            res = res and self._validate_one_link(link[1], link[0])

        return res

    def _run_tests(self):
        """
        Let user override the list of tests to be performed.

        Error trapping is handled by the validate() wrapper method.
        """
        tests = [self._validate_no_fixme(),
                 self._validate_header(),
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

    EXPECTED_YAML_HEADER = {'layout': vh.is_str,
                            'title': vh.is_str}

    EXPECTED_BOXES = {'prereq': ("Prerequisites", 1, 1)}

    # TODO Improve the following function
    def _validate_intro_section(self):
        """Validate the intro section.

        It must be a paragraph, followed by blockquoted with prereqs."""
        if vh.is_paragraph(self.ast.body, 0):
            logging.warning(
                "In {0}: "
                "The first element must be a paragraph.".format(
                    self.filename))
            return False

        if vh.is_blockquote(self.ast.body, 1):
            logging.warning(
                "In {0}: "
                "The second element must be a blockquote.".format(
                    self.filename))
            return False
        else:
            blockquote = vh.get_node_content(self.ast.body, 1)
            if vh.is_heading(blockquote, 0):
                logging.warning(
                    "In {0}: "
                    "The first element at the blockquote must be a header.".format(
                        self.filename))
                return False

            if vh.is_paragraph(blockquote, 1):
                logging.warning(
                    "In {0}: "
                    "The second element at the blockquote must be a header.".format(
                        self.filename))
                return False

        return True

    def _run_tests(self):
        parent_tests = super(IndexPageValidator, self)._run_tests()
        tests = [self._validate_intro_section()]
        return all(tests) and parent_tests


class TopicPageValidator(MarkdownValidator):
    """Validate the Markdown contents of a topic page, eg 01-topicname.md"""
    EXPECTED_YAML_HEADER = {"layout": vh.is_str,
                            "title": vh.is_str,
                            "subtitle": vh.is_str,
                            "minutes": vh.is_numeric}

    EXPECTED_BOXES = {"objectives": ("Learning Objectives", 1, 1),
                      "callout": (None, 0, float("inf")),
                      "challenge": (None, 0, float("inf"))}


class MotivationPageValidator(MarkdownValidator):
    """Validate motivation.md"""
    WARN_ON_EXTRA_HEADINGS = False

    EXPECTED_YAML_HEADER = {"layout": vh.is_str,
                            "title": vh.is_str,
                            "subtitle": vh.is_str}


class ReferencePageValidator(MarkdownValidator):
    """Validate reference.md"""
    EXPECTED_HEADINGS = ["Glossary"]
    WARN_ON_EXTRA_HEADINGS = False

    EXPECTED_YAML_HEADER = {"layout": vh.is_str,
                            "title": vh.is_str,
                            "subtitle": vh.is_str}

    def _validate_glossary(self):
        """Validate glossary entry

        Glossary entry must be formatted in conformance with Pandoc's
        ```definition_lists``` extension."""
        res = True
        glossary_finded = False
        glossary = None

        for node in self.ast.body:
            if glossary:
                logging.error(
                    "In {0}:"
                    "Extra element after glossary.".format(
                        self.filename))
                res = False
            elif glossary_finded:
                glossary = node
            else:
                if (node['t'] == "Header"
                        and vh.ast_to_string(node['c']) == "Glossary"):
                    glossary_finded = True

        if glossary is None:
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

    EXPECTED_YAML_HEADER = {"layout": vh.is_str,
                            "title": vh.is_str,
                            "subtitle": vh.is_str}


class LicensePageValidator(MarkdownValidator):
    """Validate LICENSE.md: user should not edit this file"""
    def _run_tests(self):
        """Skip the base tests; just check md5 hash"""
        # TODO: This hash is specific to the license for english-language repo
        expected_hash = '051a04b8ffe580ba6b7018fb4fd72a50'
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
    EXPECTED_YAML_HEADER = {"layout": vh.is_str,
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
SKIP_FILES = ("CONDUCT.md", "CONTRIBUTING.md",
              "DESIGN.md", "FAQ.md", "LAYOUT.md", "README.md")


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
