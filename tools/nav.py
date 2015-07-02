#!/usr/bin/python
"""
Provide file for navigation bar
"""
import glob
import os
import re
import sys

def get_files():
    """Get list of files that are part of the lesson"""
    files = glob.glob("*.md")
    files.sort()
    return [f for f in files if re.match("^[0-9]", f)]

def main(filename):
    """Find previous and next file"""
    previous_file = ""
    next_file = ""

    files = get_files()
    try:
        idx = files.index(filename)
    except ValueError:
        idx = None
    if filename == "index.md":
        next_file = files[0]
    elif filename == "reference.md":
        previous_file = files[-1]
        next_file = "discussion.md"
    elif filename == "discussion.md":
        previous_file = "reference.md"
        next_file = "instructors.md"
    elif filename == "instructors.md":
        previous_file = "discussion.md"
    elif idx is not None:
        if idx > 0:
            previous_file = files[idx - 1]
        if idx < len(files) - 1:
            next_file = files[idx + 1]
        if idx == len(files) - 1:
            next_file = "reference.md"

    previous_file = previous_file.replace(".md", ".html")
    next_file = next_file.replace(".md", ".html")

    return (previous_file, next_file)

if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print("Missing argument. Please provide the currently file.")
        exit(1)
    else:
        previous_file, next_file = main(sys.argv[1])
        if len(sys.argv) < 3 or sys.argv[2] == '-p':
            print(previous_file)
        if len(sys.argv) < 3 or sys.argv[2] == '-n':
            print(next_file)
        exit(0)
