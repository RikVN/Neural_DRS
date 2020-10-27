#!/usr/bin/env python
# -*- coding: utf8 -*-


'''Do semantic tag analysis as is outlined in the EMNLP2020 paper
   Input: either a file with the semtags per sentence
      OR: the semtags in Boxer format, such as you can see here:
      https://github.com/RikVN/DRS_parsing/blob/master/parsing/layer_data/gold/en/test.conll
      For DRS experiments you would usually want to use the released .conll files

   Score files are result files from experiment with a score on each line, like this:

   0.87
   0.45
   0.23
   ... etc

   OR matching clauses, produced clauses and gold clauses on a single line,
   so we can calculate micro F1-score:
   10 15 14
   8 8 9
   7 12 21
   ... etc

   The semtag experiments that are performed are hardcoded, check the get_semtag_exps() function'''

import argparse
from uts import flatten_list_of_list, load_float_file, get_filename, \
                load_multi_int_file, sum_two_lists
from parsing.run_boxer import get_conll_blocks, merge_by_document
from utils_counter import create_tab_list, compute_f


def create_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--semtag_file", required=True, type=str,
                        help="File with the semtags")
    parser.add_argument("-r", "--result_files", nargs="+", required=True, type=str,
                        help="Files with the results we want scores for")
    parser.add_argument("-n", "--names", nargs="+", type=str,
                        help="Names of the exps, if not added take first 6 chars of filenames")
    parser.add_argument("-c", "--conll", action="store_true", help="Input is in CoNLL format")
    parser.add_argument("-min", "--min_occ", default=10, type=int,
                        help="Minimum of docs a idv semtags should occur for the single analysis")
    parser.add_argument("-m", "--micro_fscore", action="store_true",
                        help="Score files contain 3 values for match/prod/gold clauses")
    args = parser.parse_args()
    # Check some things here
    if args.names and not len(args.names) == len(args.result_files):
        raise ValueError("Names were specified, but not same amount as number of experiment files")
    return args


def get_semtag_exps():
    '''Return dictionary and list of semtag scores we want to see'''
    # Semtag experiments, define list we look at here
    semtag_exps = {}
    # Empty list means use all sentences
    semtag_exps["All"] = []
    semtag_exps["Numerals"] = ["QUC", "MOY", "SCO", "ORD", "DAT", "DOM", "YOC", "DEC", "CLO"]
    # semtag_exps["Events"] = ["EXS", "ENS", "EPS", "EXG", "EXT"]
    semtag_exps["Attributes"] = ["QUC", "QUV", "COL", "IST", "SST",
                                 "PRI", "DEG", "INT", "REL", "SCO"]
    semtag_exps["Named Entities"] = ["PER", "GPE", "GPO", "GEO", "ORG", "ART",
                                     "HAP", "UOM", "CTC", "LIT", "NTH"]
    semtag_exps["Logic"] = ["ALT", "XCL", "DIS", "AND", "IMP", "BUT"]
    semtag_exps["Modal"] = ["NOT", "NEC", "POS"]
    semtag_exps["  Negation"] = ["NOT"]
    semtag_exps["  Possibility"] = ["POS"]
    semtag_exps["  Necessity"] = ["NEC"]
    semtag_exps["Pronouns"] = ["PRO", "HAS", "REF", "EMP"]
    semtag_exps["Comparatives"] = ["EQU", "APX", "MOR", "LES", "TOP", "BOT", "ORD"]
    # Define order in which we print the scores, also defines which ones we actually include
    semtag_exps["exp_order"] = ["All", "Modal", "  Negation", "  Possibility", "  Necessity",
                                "Logic", "Pronouns", "Attributes", "Comparatives",
                                "Named Entities", "Numerals"]
    return semtag_exps


def read_semtag_data(in_file):
    '''Read semtags as a list, one line per document'''
    return [x.strip().split() for x in open(in_file, 'r')]


def read_conll_data(in_file):
    '''Read in data in CoNLL format'''
    conll_blocks, doc_ids = get_conll_blocks(in_file)
    doc_blocks = [flatten_list_of_list(block) for block in merge_by_document(conll_blocks, doc_ids)]
    return doc_blocks


def indices_per_tag(tag_list):
    '''Get all documents (indices) for which a certain tag occurs'''
    tag_dict = {}
    for idx, tags in enumerate(tag_list):
        for tag in tags:
            if tag in tag_dict:
                # Don't add same tag twice, not needed
                if idx not in tag_dict[tag]:
                    tag_dict[tag].append(idx)
            else:
                tag_dict[tag] = [idx]
    return tag_dict


def tag_dict_to_list(exp_res, tag_dict, do_micro_f):
    '''Create a result list from the dictionary of tag results'''
    res_list = []
    for key in exp_res[0]:
        to_app = [key, len(tag_dict[key])]
        for exp in exp_res:
            # Calculate final score for this experiment for this tag
            if do_micro_f:
                final_score = "{:.1f}".format(compute_f(exp[key][0], exp[key][1],
                                              exp[key][2], f_only=True, significant=3) * 100)
            else:
                final_score = "{:.1f}".format((float(exp[key]) / float(len(tag_dict[key])) * 100))
            to_app.append(final_score)
        # Add to final list
        res_list.append(to_app)
    # Now sort the list based on occurence
    return sorted(res_list, key=lambda x: x[1], reverse=True)


def single_tag_analysis(tags, results, min_occ, do_micro_f):
    '''Calculate scores over individual tags, as long they occur often enough'''
    # For each tag, get in which document they occur
    tag_dict = indices_per_tag(tags)
    # Loop over the files to calculate the scores
    exp_res = []
    for res in results:
        # Loop over tags that occur enough and calculate the score for those tags
        score_dict = {}
        for tag in tag_dict:
            if len(tag_dict[tag]) >= min_occ:
                score_dict[tag] = [0, 0, 0] if do_micro_f else 0
                # Loop over the documents for this tag, read the scores and add
                for doc_idx in tag_dict[tag]:
                    if do_micro_f:
                        score_dict[tag] = sum_two_lists(score_dict[tag], res[doc_idx])
                    else:
                        score_dict[tag] += res[doc_idx]
        # Save final results for this experiment to list
        exp_res.append(score_dict)

    # Create list that has the results as we want to print them, e.g.
    # NOT 0.87 0.93
    return tag_dict_to_list(exp_res, tag_dict, do_micro_f)


def contains_semtag(line, semtags):
    '''Check if a line of semtags contain a semtag from a predefined list
       Important: if semtags is empty we return True'''
    if not semtags:
        return True
    for sem in line:
        if sem in semtags:
            return True
    return False


def combined_tag_analysis(tags, results, exp_dict, do_micro_f):
    '''Run the analysis here based on the files and the tags you want to look at'''
    # Loop over experiment that we want to do, as defined in exp_dict["exp_order"]
    res_list = []
    for exp_type in exp_dict["exp_order"]:
        to_add = [exp_type]
        # Loop over the number of result files
        for idx, res in enumerate(results):
            score = [0, 0, 0] if do_micro_f else 0
            num_docs = 0
            for doc_idx, cur_score in enumerate(res):
                if contains_semtag(tags[doc_idx], exp_dict[exp_type]):
                    num_docs += 1
                    if do_micro_f:
                        score = sum_two_lists(score, cur_score)
                    else:
                        score += cur_score
            # Add total docs once
            if idx == 0:
                to_add.append(str(num_docs))
            # Now add final score
            if do_micro_f:
                final_score = "{:.1f}".format(compute_f(score[0], score[1], score[2],
                                              f_only=True, significant=3) * 100)
            else:
                final_score = "{:.1f}".format((float(score) / float(num_docs) * 100))
            to_add.append(final_score)
        # Add the total scores for all experiments to the list we will print
        res_list.append(to_add)
    return res_list


def main():
    '''Main function of semtag_analysis.py'''
    args = create_arg_parser()
    # First do the data wrangling
    if args.conll:
        # Read in the full CoNLL file
        conll_data = read_conll_data(args.semtag_file)
        # Only keep the semtags in a list of lists, one list per doc
        # Important: assume semtags are in third position
        data = [[line[2] for line in doc] for doc in conll_data]
    else:
        data = read_semtag_data(args.semtag_file)

    # Read in the scores
    scores = [load_multi_int_file(in_f) for in_f in args.result_files] \
              if args.micro_fscore else [load_float_file(in_f) for in_f in args.result_files]

    # Set the names if not set to first 6 chars of filename
    names = args.names if args.names else [get_filename(in_f)[0:6] for in_f in args.result_files]

    # Define the combined experiments we want to do, hardcoded
    semtag_exp_dict = get_semtag_exps()

    # First get scores per single semtag, for a minimum amount
    single_list = single_tag_analysis(data, scores, args.min_occ, args.micro_fscore)
    for line in create_tab_list([["Tag", "Docs"] + names] + single_list,
                                "\nResults for sentences that contain individual tags:\n", "\t"):
        print(line)

    # Do the analysis for the combined semtag experiment (negation, numerals, modals, etc)
    combined_list = combined_tag_analysis(data, scores, semtag_exp_dict, args.micro_fscore)
    for line in create_tab_list([["Exp", "Docs"] + names] + combined_list,
                                "\nResults semtag experiment:\n", "\t"):
        print(line)

if __name__ == '__main__':
    main()
