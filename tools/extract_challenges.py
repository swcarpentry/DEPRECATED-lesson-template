#!/usr/bin/env python

'''Extract challenges from lessons.'''

import sys
import re


USAGE = 'usage: extract_challenges [-o output_name] [filename...]'

title_pat = re.compile(r'^>\s+.+\{.challenge\}')
block_pat = re.compile(r'^>')

def main(argv):
    '''Main driver.'''

    prog_name = argv[0]
    filenames = argv[1:]
    output_name = None
    writer = sys.stdout

    if filenames and (filenames[0] == '-o'):
        if len(filenames) < 2:
            print >> sys.stderr, USAGE
            sys.exit(1)
        output_name = filenames[1]
        filenames = filenames[2:]

    if output_name:
        writer = open(output_name, 'w')

    if filenames:
        for f in filenames:
            with open(f, 'r') as reader:
                extract(reader, writer)
    else:
        extract(sys.stdin, writer)

    if writer != sys.stdout:
        writer.close()


def extract(reader, writer):
    '''Extract challenges from reader, sending to writer.'''

    echo = False
    for line in reader:
        if title_pat.search(line):
            echo = True
        if echo and (not block_pat.search(line)):
            print >> writer
            echo = False
        if echo:
            print >> writer, line.rstrip()
    print >> writer


if __name__ == '__main__':
    main(sys.argv)
