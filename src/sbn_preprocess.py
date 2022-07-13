#!/usr/bin/env python
# -*- coding: utf8 -*-

'''Preprocess SBN file to a 1-line format used for training a seq2seq model
   It does three main things

   1) Putting SBN files in one-line format
   2) Formatting names with ~ instead of spaces, e.g. "Naomi~Osaka"
   3) Filtering empty SBNs - and also filtering them from the raw files to keep the alignment'''


import sys
import argparse


def create_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--raw", required=True, type=str,
                        help="Raw file with sentences")
    parser.add_argument("-s", "--sbn", required=True, type=str,
                        help="File with DRSs in SBN format")
    args = parser.parse_args()
    return args


def write_to_file(lst, out_file, do_strip=True):
    '''Write list to file'''
    with open(out_file, "w", encoding='utf-8') as out_f:
        for line in lst:
            if do_strip:
                out_f.write(line.strip() + '\n')
            else:
                out_f.write(line + '\n')
    out_f.close()


def main():
    '''Main function of preprocessing SBNs to a one-line format'''
    args = create_arg_parser()
    # Read in the raw sentences
    raw = [x.strip() for x in open(args.raw, 'r')]

    keep_raw = []
    cur_sbn = []
    all_sbn = []
    cur_idx = 0
    # Loop over SBN file
    for line in open(args.sbn, 'r', encoding="utf8"):
        if not line.strip():
            # Empty line, so SBN is finished, now add it
            # Only add SBN if we actually found one
            if cur_sbn:
                all_sbn.append(" ".join(cur_sbn).strip())
                keep_raw.append(raw[cur_idx])
                cur_sbn = []
            # Increase idx anyway, this way we automatically filter out the sentences
            # for which the SBN was actually empty
            cur_idx += 1
        elif not line.strip().startswith('%'):
            info = "%".join(line.strip().split('%')[0:-1])
            # Now make sure we replace space between quotes by a "~" character
            # E.g "Naomi Osaka" to "Naomi~Osaka"
            string = ''
            between_quotes = False
            for char in " ".join(info.split()):
                if char == '"':
                    between_quotes = not between_quotes
                    string += char
                elif char == ' ' and between_quotes:
                    # Space in quotes, add ~ instead
                    string += '~'
                else:
                    string += char
            cur_sbn.append(string.strip())

    # Also add the last one
    if cur_sbn:
        all_sbn.append(" ".join(cur_sbn).strip())
        keep_raw.append(raw[cur_idx])

    # Write non-empty one-line SBNs and corresponding raw sentences
    write_to_file(all_sbn, args.sbn + '.one')
    write_to_file(keep_raw, args.raw + '.keep')


if __name__ == "__main__":
    main()

