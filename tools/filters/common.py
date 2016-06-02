"""Common functions for filters"""
import pandocfilters as pf

def text2fragment_identifier(text):
    """Generate fragment identifier from text.

    - Convert to lowercase.
    - Replace white space with "-".
    - Remove ' and "."""
    return text.lower().replace(" ", "-").replace("'", "").replace('"', "")
