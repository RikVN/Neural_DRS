#!/usr/bin/env python
# -*- coding: utf8 -*-

'''
Scripts that takes a list of files and outputs a merged version of the tags of those files
This is useful when we want to combine semtagging, POS-tagging, etc, in a single file
It's possible to also indicate that for certain files we want the output in character-level
format, for example the lemma files.

We also take into account that some files contain specific tokenization, e.g. the CCG parse,
then we split based on the tokenization character (usually '***')
'''

import argparse
import sys


def create_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--input_files", required=True, nargs="*", help="Input files with lists of tags")
    parser.add_argument("-c", "--char_exts", default=[], nargs="*", help="Extension of items we put in character-level format (e.g. .lem files)")
    parser.add_argument("-t", "--tok_char", default='***', type=str, help="Character that is present in already tokenized files")
    args = parser.parse_args()
    return args


def has_ext(exts, f):
    '''Check if file ends with certain extension'''
    for ext in exts:
        if f.endswith(ext):
            return True
    return False


def get_line_representation(in_file, tok_char, char_exts):
    '''Based on an input file, return a list of lists with the representation that is desirable'''
    cur_lines = []
    for line in open(in_file, 'r'):
        if line.strip():
            # Check if input is already tokenized, then split based on tokenization char (usually '***')
            if tok_char in line:
                spl_line = line.strip().split(tok_char)
            else: # Just do tags separated by whitespace
                spl_line = line.strip().split()
            # Check if the items need to be in char-level format
            if has_ext(char_exts, in_file):
                spl_line = [" ".join(x) for x in spl_line]
            cur_lines.append(spl_line)
    return cur_lines


if __name__ == "__main__":
    args = create_arg_parser()

    # Save the file/line representation for each input file
    all_lines = [get_line_representation(in_file, args.tok_char, args.char_exts) for in_file in args.input_files]
    space_sep = ' {} '.format(args.tok_char)

    # Then merge all read input files to single output
    # Bit of a complicated loop, since we loop over all lines, all tags and all files
    for idx1 in range(len(all_lines[0])):
        out_line = []
        for idx2 in range(len(all_lines[0][idx1])):
            tags = []
            for idx3 in range(len(all_lines)):
                if idx2 < len(all_lines[idx3][idx1]): # Skip if the something went wrong
                    if all_lines[idx3][idx1][idx2] != 'FAILED-PARSE': #also don't add failed parses
                        tags.append(all_lines[idx3][idx1][idx2])
            out_line.append(" ".join(tags)) # Add tag boundary here if we want (cur not)
        # Line is done, add word boundary and print
        print(" ".join(space_sep.join(out_line).split()))
