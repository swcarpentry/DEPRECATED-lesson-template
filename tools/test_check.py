#! /usr/bin/env python

"""
Unit and functional tests for markdown lesson template validator.

Some of these tests require looking for example files, which exist only on
the gh-pages branch.   Some tests may therefore fail on branch "core".
"""

import logging
import os
import unittest

import check

# Make log messages visible to help audit test failures
check.start_logging(level=logging.CRITICAL)

MARKDOWN_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir))


class BaseTemplateTest(unittest.TestCase):
    """Common methods for testing template validators"""
    VALIDATOR = check.MarkdownValidator

    def _create_validator(self, markdown):
        """Create validator object from markdown string; useful for failures"""
        return self.VALIDATOR(markdown=markdown)


class TestIndexPage(BaseTemplateTest):
    """Test the ability to correctly identify and validate specific sections
        of a markdown file"""
    VALIDATOR = check.IndexPageValidator

    # TESTS INVOLVING DOCUMENT HEADER SECTION
    def test_headers_missing_header(self):
        validator = self._create_validator("""Blank row""")

        self.assertFalse(validator._validate_header())

    def test_headers_missing_a_line(self):
        """One of the required headers is missing"""
        validator = self._create_validator("""---
layout: lesson
---""")
        self.assertFalse(validator._validate_header())

    def test_headers_fail_with_other_content(self):
        validator = self._create_validator("""---
layout: lesson
title: Lesson Title
otherline: Nothing
---""")
        self.assertFalse(validator._validate_header())

    def test_fail_when_headers_not_yaml_dict(self):
        """Fail when the headers can't be parsed to a dict of YAML data

        This will print ::

            pandoc: YAML header is not an object "source" (line 1, column 1)

        to stderr."""
        validator = self._create_validator("""---
This will parse as a string, not a dictionary
---""")
        self.assertFalse(validator._validate_header())

    # TESTS INVOLVING SECTION TITLES/HEADINGS
    def test_index_has_valid_section_headings(self):
        """The provided index page"""
        validator = self._create_validator("""## Topics

1.  [Topic Title One](01-one.html)
2.  [Topic Title Two](02-two.html)

## Other Resources

*   [Motivation](motivation.html)
*   [Reference Guide](reference.html)
*   [Next Steps](discussion.html)
*   [Instructor's Guide](instructors.html)""")
        self.assertTrue(validator._validate_headings_order())

    def test_index_fail_when_section_heading_absent(self):
        validator = self._create_validator("""## Topics

1.  [Topic Title One](01-one.html)
2.  [Topic Title Two](02-two.html)

## Other Resources

*   [Motivation](motivation.html)
*   [Reference Guide](reference.html)
*   [Next Steps](discussion.html)
*   [Instructor's Guide](instructors.html)""")
        res = validator._validate_header()
        self.assertFalse(res)

    def test_fail_when_section_heading_is_wrong_level(self):
        """All headings must be exactly level 2"""
        validator = self._create_validator("""---
layout: page
title: Lesson Title
---
Paragraph of introductory material.

> ## Prerequisites
>
> A short paragraph describing what learners need to know
> before tackling this lesson.

### Topics

1.  [Topic Title 1](01-one.html)
2.  [Topic Title 2](02-two.html)

## Other Resources

*   [Motivation](motivation.html)
*   [Reference Guide](reference.html)
*   [Next Steps](discussion.html)
*   [Instructor's Guide](instructors.html)""")
        self.assertFalse(validator._validate_headings_order())

    def test_fail_when_section_headings_in_wrong_order(self):
        validator = self._create_validator("""---
layout: lesson
title: Lesson Title
---
Paragraph of introductory material.

> ## Prerequisites
>
> A short paragraph describing what learners need to know
> before tackling this lesson.

## Other Resources

* [Motivation](motivation.html)
* [Reference Guide](reference.html)
* [Instructor's Guide](instructors.html)


## Topics

* [Topic Title 1](01-one.html)
* [Topic Title 2](02-two.html)""")

        self.assertFalse(validator._validate_headings_order())

    def test_pass_when_prereq_section_has_correct_heading_level(self):
        validator = self._create_validator("""---
layout: lesson
title: Lesson Title
---
Paragraph of introductory material.

> ## Prerequisites
>
> A short paragraph describing what learners need to know
> before tackling this lesson.
""")
        self.assertTrue(validator._validate_intro_section())

    def test_fail_when_prereq_section_has_incorrect_heading_level(self):
        validator = self._create_validator("""
> # Prerequisites {.prereq}
>
> A short paragraph describing what learners need to know
> before tackling this lesson.
""")
        self.assertFalse(validator._validate_boxes())

    def test_missing_markdown_file_fails_validation(self):
        """Fail validation when an html file is linked without corresponding
            markdown file"""
        validator = self._create_validator("""[Broken link](nonexistent.html)""")
        self.assertFalse(validator._validate_links())

    def test_website_link_ignored_by_validator(self):
        """Don't look for markdown if the file linked isn't local-
            remote website links are ignored"""
        validator = self._create_validator("""[Broken link](http://website.com/filename.html)""")
        self.assertTrue(validator._validate_links())

    def test_malformed_website_link_fails_validator(self):
        """If the link isn't prefixed by http(s):// or ftp://, fail.
         This is because there are a lot of edge cases in distinguishing
            between filenames and URLs: err on the side of certainty."""
        validator = self._create_validator("""[Broken link](www.website.com/filename.html)""")
        self.assertFalse(validator._validate_links())

    def test_image_asset_not_found(self):
        """Image asset can't be found if path is invalid"""
        validator = self._create_validator(
            """![this is the image's title](fig/exemple.svg "this is the image's alt text")""")
        self.assertFalse(validator._validate_links())

    def test_non_html_links_are_path_sensitive(self):
        """Fails to find CSV file with wrong path."""
        validator = self._create_validator(
            """Use [this CSV](data.csv) for the exercise.""")
        self.assertFalse(validator._validate_links())

    def test_one_prereq_callout_passes(self):
        """index.md should have one, and only one, prerequisites box"""
        validator = self._create_validator("""> ## Prerequisites {.prereq}
>
> What learners need to know before tackling this lesson.
""")
        self.assertTrue(validator._validate_boxes())

    def test_two_prereq_callouts_fail(self):
        """More than one prereq callout box is not allowed"""
        validator = self._create_validator("""> ## Prerequisites {.prereq}
>
> What learners need to know before tackling this lesson.

A spacer paragraph

> ## Prerequisites {.prereq}
>
> A second prerequisites box should cause an error
""")
        self.assertFalse(validator._validate_boxes())

    def test_callout_without_style_fails(self):
        """A callout box will fail if it is missing the required style"""
        validator = self._create_validator("""> ## Prerequisites
>
> What learners need to know before tackling this lesson.
""")
        self.assertFalse(validator._validate_boxes())

    def test_callout_with_wrong_title_fails(self):
        """A callout box will fail if it has the wrong title"""
        validator = self._create_validator("""> ## Wrong title {.prereq}
>
> What learners need to know before tackling this lesson.
""")
        self.assertFalse(validator._validate_boxes())

    def test_unknown_callout_style_fails(self):
        """A callout whose style is unrecognized by template is invalid"""
        validator = self._create_validator("""> ## Any title {.callout}
>
> What learners need to know before tackling this lesson.
""")
        self.assertFalse(validator._validate_boxes())

    def test_block_ignored_sans_heading(self):
        """
        Blockquotes only count as callouts if they have a heading
        """
        validator = self._create_validator("""> Prerequisites {.prereq}
>
> What learners need to know before tackling this lesson.
""")
        callout_nodes = validator.ast.get_boxes()
        self.assertEqual(len(callout_nodes), 0)

    def test_callout_heading_must_be_l2(self):
        """Callouts will fail validation if the heading is not level 2"""
        validator = self._create_validator("""> ### Prerequisites {.prereq}
>
> What learners need to know before tackling this lesson.
""")
        self.assertFalse(validator._validate_boxes())

    def test_fail_if_fixme_present_all_caps(self):
        """Validation should fail if a line contains the word FIXME (exact)"""
        validator = self._create_validator("""Incomplete sentence (FIXME).""")
        self.assertFalse(validator._validate_no_fixme())

    def test_fail_if_fixme_present_mixed_case(self):
        """Validation should fail if a line contains the word FIXME
        (in any capitalization)"""
        validator = self._create_validator("""Incomplete sentence (FiXmE).""")
        self.assertFalse(validator._validate_no_fixme())


class TestTopicPage(BaseTemplateTest):
    """Verifies that the topic page validator works as expected"""
    VALIDATOR = check.TopicPageValidator

    def test_headers_fail_because_invalid_content(self):
        """The value provided as YAML does not match the expected datatype"""
        validator = self._create_validator("""---
layout: lesson
title: Lesson Title
subtitle: A page
minutes: not a number
---""")
        self.assertFalse(validator._validate_header())

    def test_topic_page_should_have_no_headings(self):
        """Requirement according to spec; may be relaxed in future"""
        validator = self._create_validator("""
## Heading that should not be present

Some text""")
        self.assertFalse(validator._validate_header())


    def test_callout_style_passes_regardless_of_title(self):
        """Verify that certain kinds of callout box can be recognized solely
        by style, regardless of the heading title"""
        validator = self._create_validator("""> ## Learning Objectives {.objectives}
>
> * All topic pages must have this callout

> ## Some random title {.callout}
>
> Some informative text""")

        self.assertTrue(validator._validate_boxes())

    def test_callout_style_allows_duplicates(self):
        """Multiple blockquoted sections with style 'callout' are allowed"""
        validator = self._create_validator("""> ## Learning Objectives {.objectives}
>
> * All topic pages must have this callout

> ##  Callout box one {.callout}
>
> Some informative text

Spacer paragraph

> ## Callout box two {.callout}
>
> Further exposition""")
        self.assertTrue(validator._validate_boxes())


class TestMotivationPage(BaseTemplateTest):
    """Verifies that the instructors page validator works as expected"""
    VALIDATOR = check.MotivationPageValidator


class TestReferencePage(BaseTemplateTest):
    """Verifies that the reference page validator works as expected"""
    VALIDATOR = check.ReferencePageValidator

    def test_missing_glossary_definition(self):
        validator = self._create_validator("")
        self.assertFalse(validator._validate_glossary())

    def test_only_definitions_can_appear_after_glossary_heading(self):
        validator = self._create_validator("""## Glossary

Key Word 1
:   Definition of first term

Paragraph

Key Word 2
:   Definition of second term
""")
        self.assertFalse(validator._validate_glossary())

    def test_definition_with_two_lines(self):
        validator = self._create_validator("""## Glossary

Key Word
:   Definition of first term.
    Second line of the definition.
""")
        self.assertTrue(validator._validate_glossary())

    def test_glossary(self):
        validator = self._create_validator("""## Glossary

Key Word 1
:   Definition of first term
    Second line of the definition.

Key Word 2
:   Definition of second term
""")
        self.assertTrue(validator._validate_glossary())


class TestInstructorPage(BaseTemplateTest):
    """Verifies that the instructors page validator works as expected"""
    VALIDATOR = check.InstructorPageValidator


class TestLicensePage(BaseTemplateTest):
    VALIDATOR = check.LicensePageValidator


class TestDiscussionPage(BaseTemplateTest):
    VALIDATOR = check.DiscussionPageValidator


if __name__ == "__main__":
    unittest.main()
