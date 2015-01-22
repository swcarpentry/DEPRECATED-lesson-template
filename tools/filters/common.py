"""Common functions for filters"""

def text2fragment_identifier(text):
    """Generate fragment identifier from text.

    - Convert to lowercase.
    - Replace white space with "-".
    - Remove ' and "."""
    return text.lower().replace(" ", "-").replace("'", "").replace('"', "")
