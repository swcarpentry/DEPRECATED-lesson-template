#! /usr/bin/env python

import logging
import re
import sys

import json
import pypandoc
import pandocfilters

import filters.common as fc

try:  # Hack to make codebase compatible with python 2 and 3
  basestring
except NameError:
  basestring = str


# Common validation functions
def ast_to_string(ast):
    """Convert Pandoc AST to string."""
    return pandocfilters.stringify(ast)


def is_str(text):
    """Validate whether the input is a non-blank python string"""
    return isinstance(text, basestring) and len(text) > 0


def is_numeric(text):
    """Validate whether the string represents a number (including unicode)"""
    try:
        float(text)
        return True
    except ValueError:
        return False

def is_blockquote(ast, position=0):
    """Check if given node of AST is a blockquote."""
    return ast[position] and ast[position]['t'] != "BlockQuote"

def is_heading(ast, position=0):
    """Check if given node of AST is a heading."""
    return ast[position] and ast[position]['t'] != "Header"

def is_paragraph(ast, position=0):
    """Check if given node of AST is a paragraph."""
    return ast[position] and ast[position]['t'] != "Para"

def is_box(ast_node):
    """Check if is a box, i.e.
    blockquotes whose first child element is a heading"""
    if (ast_node["t"] == "BlockQuote"
        and len(ast_node["c"]) > 1
        and ast_node["c"][0]["t"] == "Header"):
        return True
    else:
        return False

def get_node_content(ast, position):
    """Return the content of the givem node of AST."""
    return ast[position]['c']
def get_box_level(ast_node):
    """Return the level of the box."""
    return ast_node["c"][0]["c"][0]

def get_box_title(ast_node):
    """Return the title of the box."""
    return ast_to_string(ast_node['c'][0])

def get_box_type(ast_node):
    """Return the type of the box."""
    box_type = ast_node['c'][0]['c'][1][1]
    if len(box_type) > 0:
        box_type = box_type[0]
    else:
        box_type = None

    return box_type

### Pandoc AST Helper
class PandocAstHelper(object):
    """Basic helper functions
    for working with the internal abstract syntax tree (ast)
    produced by Pandoc parser"""
    def __init__(self, markdown):
        self.header, self.body = self._parse_markdown(markdown)

        self.anchors = []

        def get_anchors(key, val, format, meta):
            if key == "Header":
                self.anchors.append(val[1][0])
            if key == "DefinitionList":
                for definition in val:
                    self.anchors.append(fc.text2fragment_identifier(ast_to_string(definition[0])))

        pandocfilters.walk(self.body, get_anchors, "", {})

    def _parse_markdown(self, markdown):
        ast = json.loads(pypandoc.convert(''.join(markdown),
                                          'json',
                                          'markdown'))
        return ast[0]["unMeta"], ast[1]

    def _get_info_from_header(self, keyword):
        """Get the value for a keyword or None if the keyword doesn't exist."""
        if keyword in self.header:
            return ast_to_string(self.header["title"])
        else:
            return None

    def get_doc_title(self):
        """Get the document title of the document."""
        return self._get_info_from_header("title")

    def get_doc_subtitle(self):
        """Get the document subtitle of the document."""
        return self._get_info_from_header("subtitle")

    def get_headings(self):
        """Returns a list of (level, title) of sections"""
        headings = []
        for ast_node in self.body:
            if ast_node["t"] == "Header":
                headings.append((ast_node["c"][0],
                                 ast_to_string(ast_node["c"][2])))

        return headings

    def get_boxes(self):
        boxes = []

        for ast_node in self.body:
            if is_box(ast_node):
                boxes.append(ast_node)

        return boxes
