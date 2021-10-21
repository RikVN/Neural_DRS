#!/usr/bin/env python
# -*- coding: utf8 -*-

'''Script that calculates F-score by sentence length for number of input-files or folders
   Creates a plot using matplotlib'''

import argparse
import os
import matplotlib
# Force matplotlib to not use any Xwindows backend.
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def create_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_files", required=True, nargs="*",
                        help="Files with all individual F-scores")
    parser.add_argument("-n", "--names", default='', nargs="*",
                        help="Names of the experiment, if not added take from filenames")
    parser.add_argument("-s", "--sentences", required=True, type=str,
                        help="File with the tokenized (!) sentences")
    parser.add_argument("-m", "--min_occurrence", default=8, type=int,
                        help="Minimum number of times a certain sen-length should occur")
    parser.add_argument("-o", "--output_file", default='plot.pdf', type=str,
                        help="Location of output-file (default plot.pdf)")
    parser.add_argument("-noc", "--no_colors", action="store_true",
                        help="Don't add colors in the PDF")
    args = parser.parse_args()
    return args


def get_sen_lengths(sent_file):
    '''Return list of sentences and a list of sentence length per sentence'''
    sents = [x.strip() for x in open(sent_file, 'r')]
    sen_lengths = [len(sen.split()) for sen in sents]
    return sents, sen_lengths


def read_scores(in_f):
    '''Read the scores from an input-file'''
    if os.path.isfile(in_f):
        return [float(x.strip()) for x in open(in_f, 'r')]
    raise ValueError("{0} does not exist".format(in_f))


def get_scores(input_files):
    '''Get all input files and return the scores"
       Also keep track of the file-names if names were not specified'''
    scores, file_names = [], []
    for in_f in input_files:
        if os.path.isfile(in_f):
            scores.append(read_scores(in_f))
            file_names.append(in_f.split('/')[-1])
    return scores, file_names


def check_validity(sents, sen_lengths, scores):
    '''Check if all the values have the same lengths'''
    assert len(sents) == len(sen_lengths)
    for score_list in scores:
        assert len(score_list) == len(sents), "{0} vs {1}".format(len(score_list), len(sents))


def get_max_sen_len(sen_lengths, threshold):
    '''Get the highest number of sentences for which we still have enough sentences'''
    for idx in range(3, max(sen_lengths) + 1):
        if sen_lengths.count(idx) < threshold:
            return idx - 1  # return previous idx if this one doesn't make it
    return ValueError("Did not find a max sen-length -- check value of -m and --min_occurrence: {0}"
                      .format(threshold))


def create_empty_list(max_sen_len):
    '''Create empty lists of lists this way to ensure lists are not linked'''
    f_list = [[]]
    for _ in range(max_sen_len):
        f_list.append([])
    return f_list


def avg_per_length(scores, sen_lengths, min_sen_len, max_sen_len):
    '''Produce the list with average F-scores per sentence-length for each score-list'''
    avg_scores = []
    sen_range = range(min_sen_len, max_sen_len + 1)
    for score_list in scores:
        length_counts = [0] * (max_sen_len + 1)
        f_list = create_empty_list(max_sen_len)
        # Now fill the list of scores per sen-len
        for idx, length in enumerate(sen_lengths):
            if length in sen_range:
                length_counts[length] += 1
                f_list[length].append(score_list[idx])
        # Then average all the scores
        f_list = f_list[min_sen_len:]
        avg_scores.append([float(sum(x)) / float(len(x)) for x in f_list])
    return avg_scores, length_counts[min_sen_len:], sen_range


def make_plot(avg_scores, file_names, sen_range, output_file, do_print=False,
              no_colors=False, num_sents=[]):
    '''Finally make the plot that shows the sentence length files'''
    matplotlib.rc('xtick', labelsize=13)
    matplotlib.rc('ytick', labelsize=13)
    # Start with figure
    _, ax = plt.subplots()

    # Set colors and styles
    line_styles = ["--", "--X", "--^", "--v", "--s", "--o", "--*"]
    if no_colors:
        line_styles = ['k--', 'k--.', 'k--+', 'k--v', 'k--s', 'k--*']
    else:
        ax.set_prop_cycle(color=["gold", "cornflowerblue", "lightgreen",
                                 "orange", "lightcoral", "chocolate", "purple"])

    # Do the actual plotting here
    for idx, (avg_score, name) in enumerate(zip(avg_scores, file_names)):
        if do_print:
            print('\nF-averages {0}:\n'.format(name), [round(x, 2) for x in avg_score])
        plt.plot(sen_range, [float(a) * 100 for a in avg_score],
                 line_styles[idx], lw=2.5, label=name)

    # Add necessary information
    # ax.set_ylim([78, 93]) # perhaps needed
    plt.xlabel('Document length (tokens)', size=15)
    plt.ylabel('F-score', size=16)
    # Set legend, perhaps in different location, depends on your graph
    plt.legend(loc=(0.105, 0.05), shadow=True, fontsize=13)

    # Set double axis maybe
    if num_sents:
        x_labels = ["{0}\n{1}".format(num, count) for num, count in zip(sen_range, num_sents)]
        _ = ax.set(xticks=sen_range, xticklabels=x_labels)
    # And save the plot
    plt.savefig(output_file, format='pdf', bbox_inches="tight")


def main():
    '''Main function for senlen_plot.py'''
    # Read in arguments
    args = create_arg_parser()
    # Get sentences and sentence lengths
    sents, sen_lengths = get_sen_lengths(args.sentences)
    # Get a list of lists, including all files with all scores
    scores, file_names = get_scores(args.input_files)
    # If names are not specified, use filenames
    if args.names:
        file_names = args.names
    # Check if all input is valid
    check_validity(sents, sen_lengths, scores)

    # Get min and max sen-len (max based on minimum number of occurence, min is set)
    min_sen_len = 3
    max_sen_len = get_max_sen_len(sen_lengths, args.min_occurrence)

    # Produce the list with average F-scores per sentence-length for each score-list
    avg_scores, length_counts, sen_range = avg_per_length(scores, sen_lengths,
                                                          min_sen_len, max_sen_len)
    # Now plot the final figure
    make_plot(avg_scores, file_names, sen_range, args.output_file,
              do_print=True, no_colors=args.no_colors, num_sents=length_counts)

if __name__ == "__main__":
    main()
