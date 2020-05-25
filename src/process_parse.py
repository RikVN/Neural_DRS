#!/usr/bin/env python
# -*- coding: utf8 -*-

'''Process the output of a easyCCG parsed file to a format that we will work with for (neural) semantic parsing'''

import re
import sys
import argparse

# Regexes for recognizing categories and start lines
TOKEN_PATTERN = re.compile(r' *t\((,|[^,]+)')
ATOMIC_CATEGORY_PATTERN = re.compile(r'(?<=[\\(/ ])[a-z]+')
FEATURE_OR_VARIABLE_PATTERN = re.compile(r':([a-z]+|[A-Z])')


def repl_atomic_category(match):
    return match.group(0).upper()


def create_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--input_file", required=True, type=str, help="Input file with sentences that need to be parsed")
    parser.add_argument("-t", "--tok_file", required=True, type=str, help="Input file with tokenized sentences")
    parser.add_argument("-tok", "--tokenize", action='store_true', help="Tokenize the individual categories, adding a space character and dividing in separate characters")
    parser.add_argument("-s", "--separator", default="***", type=str, help="Separator between tokens for parse")
    args = parser.parse_args()
    return args


def tokenize_cat(cat):
    '''Tokenize a category, e.g. change (S[dcl]/ NP) to ( S [dcl] / NP )'''
    # Treat all these chars as separate tokens
    tok_chars = ['(', ')', '\\', '/']
    for ch in tok_chars:
        cat = cat.replace(ch, ' ' + ch + ' ')
    # Single space for opening square bracket
    cat = cat.replace('[', ' [')
    # Resolve multiple spaces
    return " ".join(cat.split())


if __name__ == '__main__':
    args = create_arg_parser()

    # Load tokenized sentences, so that we can print enough "FAILED-PARSE" tokens if parse failed
    # This is mainly because AllenNLP needs a tag per token
    sents = [x.strip().split() for x in open(args.tok_file, 'r')]

    # Add spaces around the separator for printing
    sep = " {0} ".format(args.separator)
    cur_cats = []
    prev_new = False
    cur_idx = 0

    # Loop over input parse file
    for line in open(args.input_file, 'r'):
        if not line.strip():
            if cur_cats:
                # Newline means we finished current parse, move on to next
                print(" ".join(sep.join(cur_cats).split()))
                cur_idx += 1
                cur_cats = []
            elif prev_new:
                # Previously we also saw a newline, this happens for failed parse
                # So just output that on a new line and move on to the next
                failed_list = ["FAILED-PARSE" for x in sents[cur_idx]]
                print (" ".join(failed_list))
                cur_idx += 1
            prev_new = True
            # Else the previous line had text, but there are no cats, this can happen in
            # the beginning of the parse file, just do nothing then
        else:
            # First get the token from the parse line if it's there
            prev_new = False
            match = TOKEN_PATTERN.match(line)
            if match:
                cat = match.group(1)
                # Upper-case atomic parts of basic categories:
                cat = re.sub(ATOMIC_CATEGORY_PATTERN, repl_atomic_category, ' ' + cat)[1:]
                # Use [] instead of : for features and variables:
                cat = re.sub(FEATURE_OR_VARIABLE_PATTERN, r'[\1]', cat)
                # We have the category, check if we want to tokenize
                if args.tokenize:
                    cat = tokenize_cat(cat)
                cur_cats.append(cat)

    # If file didn't end with a newline, print output we still had saved
    if cur_cats:
        print(" ".join(sep.join(cur_cats).split()))
