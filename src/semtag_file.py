#!/usr/bin/env python
# -*- coding: utf8 -*-

'''
Script that semtags a file and puts it in the format of one line per sentence, space delimited
Must provide location of the TnT tagger and a TNT model as arguments
TnT can only be obtained by emailing Thorsten Brants filling out the license:
http://www.coli.uni-saarland.de/~thorsten/tnt/
'''

import argparse
import sys
import subprocess
from uts import write_to_file

def create_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--input_file", required=True, type=str, help="Input file with sentences that need to be semtagged")
    parser.add_argument("-m", "--model", required=True, type=str, help="Semtagging model that is used")
    parser.add_argument("-t", "--tnt", required=True, type=str, help="Location of TNT tagger")
    parser.add_argument("-e", "--extension", default='.conv', type=str, help="Extension that is added to the converted file -- convert from normal sentence format to TNT format")
    args = parser.parse_args()
    return args


def convert_file(in_file, ext):
    '''Convert the input file with sentences to the TNT format with each token on
       its own line and newlines between sentences'''
    new_lines = []
    for line in open(in_file, 'r'):
        if new_lines:
            new_lines.append('')
        for token in line.split():
            new_lines.append(token)
    write_to_file(new_lines, in_file + ext)


def convert_back(output):
    '''Convert the TNT format back to one semtag per line'''
    new_output = []
    cur_line = []
    for line in output.split('\n'):
        if not line.strip():
            new_output.append(" ".join(cur_line))
            cur_line = []
        else:
            cur_line.append(line.split()[-1])
    if cur_line:
        new_output.append(" ".join(cur_line))
    return new_output


if __name__ == "__main__":
    args = create_arg_parser()

    # First put the file in the correct format, with each token on its own line
    # and a newline between new sentences
    convert_file(args.input_file, args.extension)

    # Do the actual semtagging here with TnT + model
    output = subprocess.check_output('{0}tnt -v0 {1} {2}'.format(args.tnt, args.model, args.input_file + args.extension), shell=True).decode()

    # Convert the output back to one tag per line and write final output
    sent_output = convert_back(output)
    for s in sent_output:
        print(s)
