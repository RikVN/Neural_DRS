#!/usr/bin/env python
# -*- coding: utf8 -*-

'''Format check the feature extraction script, all extensions should have same amount of lines,
   with the lines also being the same length'''

import re
import sys
import argparse


def create_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--input_file", required=True, type=str, help="Raw input-file (CCG-ready though)")
    parser.add_argument("-e", "--extensions", default=['tok', 'sem', 'pos', 'lem', 'ccg', 'dep'], nargs="*", type=str, help="Extensions of the input file")
    args = parser.parse_args()
    return args


def load_split_file(in_f):
    '''Load a file and split sentences'''
    return [x.strip().split() for x in open(in_f, 'r')]


if __name__ == '__main__':
    args = create_arg_parser()
    dic = {}
    # Loop over extensions to save all the files in a dictionary
    for ext in args.extensions:
        add_ext = ext if ext.startswith('.') else '.' + ext
        dic[add_ext] = load_split_file(args.input_file + add_ext)

    # Check if all files have the same length
    lengths = set()
    for key in dic:
        lengths.add(len(dic[key]))
    # Error if lengths differ
    if len(lengths) != 1:
        for key in dic:
            print (key, len(dic[key]))
        raise ValueError("Unequal lengths for total lines, check above")

    # Check if all individual items have the same length
    total_len = next(iter(lengths))
    for idx in range(total_len):
        cur_lengths = set()
        for key in dic:
            cur_lengths.add(len(dic[key][idx]))
        # Error if lengths differ
        if len(cur_lengths) != 1:
            for key in dic:
                if key in ['.tok', 'tok']:
                    print (" ".join(dic[key][idx]))

                print (key, len(dic[key][idx]))
            raise ValueError("Unequal lengths for idv item, check above")

    print("All feature files have correct lengths")
