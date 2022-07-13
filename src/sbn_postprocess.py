#!/usr/bin/env python
# -*- coding: utf8 -*-

'''
Script that restores SBN output when doing an AllenNLP experiment.
The input file is a json file, restore output based on vocab.
'''

import argparse
import os
import re
from uts import write_to_file, read_allennlp_json_predictions


def create_arg_parser():
    parser = argparse.ArgumentParser()
    # Input, output and signature files
    parser.add_argument("-i", "--input_file", required=True, type=str,
                        help="Input file with output of a (neural) DRS parser")
    parser.add_argument("-o", "--output_file", required=True, type=str,
                        help="Output file we write the restored DRSs to")
    parser.add_argument("-v", "--vocab", type=str, required=True,
                        help="Vocab of AllenNLP experiment")
    parser.add_argument("-m", "--min_tokens", type=int, default=5,
                        help="Minimum amount of tokens. If not enough tokens we take different beam answer")
    args = parser.parse_args()
    if args.input_file == args.output_file:
        raise ValueError("Input and output file are the same")
    return args


def do_postprocess(in_file, out_file, vocab, min_tokens):
    '''Do postprocessing of SBN output files'''
    lines = read_allennlp_json_predictions(in_file, vocab, min_tokens)
    # Replace ~ by spaces since we did that during training
    out = [x.replace("~", " ") for x in lines]
    write_to_file(out, args.output_file)


if __name__ == "__main__":
    args = create_arg_parser()
    do_postprocess(args.input_file, args.output_file, args.vocab, args.min_tokens)
