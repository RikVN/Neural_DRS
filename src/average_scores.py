#!/usr/bin/env python
# -*- coding: utf8 -*-

'''
Script that reads in Counter output files and outputs some statistics (average, highest score, lowest, std dev)
Input is a folder, which should contain files like eval1.txt, eval2.txt...etc
'''

import argparse
import os
import numpy as np
import scipy.stats as st #for confidence interval


def create_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", required=True, type=str, help="Main evaluation folder of the experiment")
    parser.add_argument("-o", default='', type=str, help="Output file, if not added we just add 'avg_scores.txt' to args.f")
    args = parser.parse_args()
    return args


def get_eval_files(fol):
    '''Get all evaluation files and sort them
       Files should start with "eval" '''
    return sorted([os.path.join(fol, f) for f in os.listdir(fol) if os.path.isfile(os.path.join(fol, f)) and f.startswith('eval')])


def get_scores(eval_files, line_id):
    '''Return a list of scores based on the files and indicator of the line to find'''
    scores = []
    for eval_file in eval_files:
        for line in open(eval_file, 'r'):
            if line.startswith(line_id):
                scores.append(float(line.split()[-1]))
    return scores


if __name__ == "__main__":
    args = create_arg_parser()
    # Take line of file that starts with this string, so avg f/p/r
    line_ids = ['F-score', 'Precision', 'Recall']
    eval_files = get_eval_files(args.f)
    if eval_files:
        # Get file to write to
        avg_file = args.o if args.o else args.f + 'avg_scores.txt'

        # Get the F-scores and save all output information
        with open(avg_file, 'w') as out_f:
            for line_id in line_ids:
                scores = get_scores(eval_files, line_id)
                # Print the statistics
                out_f.write("For score-type: {6}\nRuns: {3}\nAll scores: {7}\nHighest score: {0}\nLowest score : {1}\nAverage score: {2}\nStandard deviation: {4}\nConfidence interval: {5}\n\n".format(max(scores), min(scores), float(sum(scores)) / float(len(scores)), len(scores), np.std(scores), [round(x, 4) for x in st.t.interval(0.95, len(scores)-1, loc=np.mean(scores), scale=st.sem(scores))], line_id, ", ".join([str(x) for x in scores])))
        out_f.close()
    else:
        print("No counter evaluation files were found -- should start with 'eval'")
