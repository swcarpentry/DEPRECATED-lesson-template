#!/usr/bin/env python
"""Pandoc filter to fix links for EPUB version.

Usage:

    pandoc source.md --filter=epub.py --output=output.html
"""
import re

import pandocfilters as pf

import common

def fix_link_for_epub(key, value, format, meta):
    """All local links must be only fragment identifier."""
    if key == "Link":
        link = value[1][0]
        if not re.match("https?:", link):
            if "#" in link:
                value[1][0] = "#{0}".format(link.split('#')[-1])
            else:
                value[1][0] = "#{0}".format(
                        common.text2fragment_identifier(pf.stringify(value[0])))

            return {"t": key,
                    "c": value}

if __name__ == '__main__':
    pf.toJSONFilter(fix_link_for_epub)
