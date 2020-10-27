#!/usr/bin/env python
# -*- coding: utf8 -*-

'''
Script that evaluates DRS parsing experiments. Output files should already exist in a folder and
should be identifiable by prefix/suffixes. Make sure to check all the arguments in
create_arg_parser() so that the script has access to all the resources it needs.
'''


import argparse
import os
import subprocess
from utils_counter import create_tab_list, compute_f
from wordnet_dict_en import en_sense_dict
from senlen_plot import get_max_sen_len, avg_per_length, make_plot
from average_scores import AverageScores
from approximate_randomization import sign_test
from semtag_analysis import get_semtag_exps, read_conll_data, combined_tag_analysis, \
                            single_tag_analysis
from uts import get_drss, print_list, num_common_elements, write_to_file, \
                sum_two_lists, is_operator, is_role, is_concept, mkdir, flatten_list_of_list, \
                print_drs, load_multi_idv_scores, load_sent_file, floats_in_line, get_num_dummies, \
                average_list, first_larger_than_zero_idx, num_items_over_zero, \
                start_dict_empty_list, most_common, get_full_files_in_folder, get_filename, \
                average_columns, transpose_list, average_difference, get_invalid_indices, \
                avg_nums_in_line


def create_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--folders", required=True, nargs="*", type=str,
                        help="Number of folders (or files) that we want to analyse")
    # If you submit a folder, it's important that we can recognize which files you want to include
    # Possible to set a prefix and/or suffix (extension) here
    parser.add_argument("-p", "--prefix", default='',
                        help="Prefix that all eval/output files should start with (for folder)")
    parser.add_argument("-de", "--drs_ext", default='',
                        help="Extension of the output files we will find in the folder")
    # Save all new results in this working folder
    parser.add_argument("-w", "--working", default='', type=str,
                        help="Working folder in which we save results (default is current dir)")
    # Gold sentences/DRSs that we want to compare our output with,
    # only important for a specific analysis of two experiments
    parser.add_argument("-s", "--sentences", default='DRS_parsing/data/pmb-3.0.0/gold/dev.txt.raw',
                        help="Raw sentences that we want to know, default 3.0.0 gold dev")
    parser.add_argument("-d", "--dev_drss", default='DRS_parsing/data/pmb-3.0.0/gold/dev.txt',
                        help="Gold DRSs that go with the sentences, default 3.0.0 gold dev")
    # Train DRSs are used for the most-frequent-sense analysis
    parser.add_argument("-td", "--train_drss", default='DRS_parsing/data/pmb-3.0.0/gold/train.txt',
                        help="Gold train DRSs that we use for the sense analysis")
    # Tokenized sentences we need for the sentence-length plot
    parser.add_argument("-t", "--tokenized_sentences",
                        default='DRS_parsing/data/pmb-3.0.0/gold/dev.txt.raw.tok',
                        help="Tokenized sentences of gold output, default PMB 3.0.0 dev")
    # Layer data is needed for the semtag analysis
    parser.add_argument("-l", "--layer_data",
                        default='DRS_parsing/parsing/layer_data/gold/en/dev.conll',
                        help="Gold tags of the 6 layers for the dev set (optional)")
    # Location of counter and referee, needed to get the F-scores
    parser.add_argument("-c", "--counter",
                        default='DRS_parsing/evaluation/counter.py', help="Location of counter")
    parser.add_argument("-sig", "--sig_file",
                        default='DRS_parsing/evaluation/clf_signature.yaml',
                        help="Location of referee sig file")
    parser.add_argument("-th", "--threads", default=8, type=int,
                        help="Parallel threads for running Counter")
    # Argument for specific analysis of best/worst DRSs, number of sentences we return
    parser.add_argument("-r", "--ret", default=5, type=int,
                        help="How many sentences do we return? Always do from both sides")
    # Argument for the statistical significance test
    parser.add_argument("-ra", "--randomizations", default=1000, type=int,
                        help="Number of randomizations we do for the significance test")
    # Arguments for the sentence length plot
    parser.add_argument("-n", "--names", default='', nargs="*",
                        help="Names of the experiment, if not added do Exp1, Exp2, etc")
    parser.add_argument("-m", "--min_occurrence", default=8, type=int,
                        help="Minimum number of times a certain sen-length should occur")
    parser.add_argument("-mi", "--min_sen_len", default=3, type=int,
                        help="Minimum sentence length that we want to plot")
    parser.add_argument("-o", "--output_file", default='', type=str,
                        help="Location of sentence length plot (default args.w + senlen_plot.pdf)")
    # Arguments for how to show the output
    parser.add_argument("-sgn", "--significant", default=3, type=int,
                        help="Significant numbers (default 3)")
    parser.add_argument("-la", "--latex", action="store_true",
                        help="Print tables in latex format with & separator")
    # Argument if we want to analyse the relative best/worst DRSs, show gold and outputs
    parser.add_argument("-a", "--analyse_indices", nargs="*", type=int,
                        help="Indices of the worst DRSs (both ways) that we will analyse")
    # File we print (average) prod/gold/match scores to combined with sen len, for statistics in R
    parser.add_argument("-sf", "--stats_file", default='', help="Print statistics to this file")
    # Use this if you want to get the output step by step, by pressing enter
    parser.add_argument("-wait", "--wait_for_input", action="store_true",
                        help="Wait for user input (enter) before doing next experiment")
    args = parser.parse_args()
    return args


def print_divider():
    '''Print a divider between experiments'''
    print("\n" + "-" * 70 + "\n")
    if wait_for_input:
        # Random input so we can see results 1 by 1 easier
        _ = input()


class Results:
    '''Class to keep track of a single DRS experiment.
       Often with multiple output files due to multiple runs)'''
    # Arguments that take care of running different types of Counter
    extra_args_dict = {"idv": "-r 10 -ms -al -ms_file $NEW_FILE", "eval": "-r 10 -prin",
                       "sense": "-r 10 -dse"}
    # Set line indicators to find results of fine-grained Counter scores, so we can average them
    # Honestly, this is a bit hacky, but it should work
    full_indicators = ["Clauses prod", "Clauses gold", "Matching clauses", "Prec", "Rec", "F1",
                       "Operators", "Roles", "Concepts", "Nouns", "Verbs",
                       "Adjectives", "Adverbs", "Events"]
    full_line_indices = [5, 6, 12, 14, 15, 16, 20, 21, 22, 23, 24, 25, 26, 27]
    indicators = ["Clauses prod", "Clauses gold", "Matching clauses", "Prec", "Rec", "F1"]
    line_indices = [5, 6, 12, 14, 15, 16]
    # Possible layers for layer_data
    layers = ["tok", "sym", "sem", "cat", "sns", "rol"]

    def __init__(self, folder, prefix, name, drs_ext, working_folder, gold_drs_file,
                 counter, threads, sig_file, layer_data):
        self.folder = folder
        self.prefix = prefix
        self.drs_ext = drs_ext
        self.working_folder = working_folder
        self.gold_drs_file = gold_drs_file
        self.counter = counter
        self.threads = threads
        self.sig_file = sig_file
        self.layer_data = layer_data
        self.name = name
        self.exp_name = name
        # Find the output files by prefix and extension
        self.set_output_files()
        assert len(self.output_files) > 0, "No output files found in folder {0}".format(self.folder)
        self.num_files = len(self.output_files)

    def set_output_files(self):
        '''Find the output files we will be working with'''
        if os.path.isfile(self.folder):
            # We work with a single file, return that
            self.output_files = [self.folder]
        else:
            # Get all files in folder, filter based on possible prefix and extension
            ret_files = get_full_files_in_folder(self.folder)
            if self.prefix:
                ret_files = [fil for fil in ret_files if get_filename(fil).startswith(self.prefix)]
            if self.drs_ext:
                ret_files = [fil for fil in ret_files if get_filename(fil).endswith(self.drs_ext)]
            self.output_files = sorted(ret_files)

    def create_result_files(self):
        '''Load and create all the result files here, based on the output files'''

        # Create the general evaluation and the individual evaluation files
        # If they already exist we can just read them
        self.idv_files = self.produce_counter_files("idv")
        self.eval_files = self.produce_counter_files("eval")
        self.sense_files = self.produce_counter_files("sense")

        # Check if we found some and that they are the same size
        assert len(self.idv_files) > 0 and len(self.idv_files) == len(self.output_files) \
               == len(self.eval_files) == len(self.sense_files)

        # Read in average F1, precision and recall (and std dev + confidence interval)
        self.avg_exp_info = AverageScores(self.working_folder + "eval/", "", False, self.prefix)
        self.avg_exp_info.calc_scores()

        # Now actually load the individual scores and the output files
        self.out_drss = [get_drss(in_file) for in_file in self.output_files]
        self.multi_idv_scores = load_multi_idv_scores(self.idv_files)
        self.idv_scores = [[compute_f(match, prod, gold, significant=significant, f_only=True)
                            for match, prod, gold in idv_sc] for idv_sc in self.multi_idv_scores]
        self.avg_idv_scores = self.average_idv_multi()
        self.avg_idv_fscores = [compute_f(match, prod, gold, significant=significant, f_only=True)
                                for match, prod, gold in self.avg_idv_scores]

        # For the finegrained numbers we have to average the files as well
        self.avg_fine = self.avg_finegrained(self.eval_files,
                                             self.full_indicators, self.full_line_indices)

        # Do something similar for the files with average sense scores
        self.avg_sense = self.avg_finegrained(self.sense_files, self.indicators, self.line_indices)

        # We also want to do an individual clause analysis
        mkdir(self.working_folder + "clause/")
        self.avg_clause = avg_clause_information(self.output_files, self.working_folder + "clause/",
                                                 self.gold_drs_file, self.counter, self.sig_file)

        # Calculate some extra statistics that are not in the Counter fine-grained scores
        self.set_extra_stats()

        # If there is layer data specified, read all the layers
        if self.layer_data:
            self.add_layer_data()

        # Sanity check:  F1, prec, rec should be the same for avg and fine
        print("Sanity check F1:", round(self.avg_exp_info.score_dict["F-score"][4],
                                        significant), self.avg_fine["F1"])

    def set_extra_stats(self):
        '''Calculate some extra statistics that are not given by counter'''
        num_f = self.num_files
        self.extra_stats = {}
        self.extra_stats["extra_stats"] = ["# illformed", "# perfect (avg)", "# perfect (all {0})"
                                           .format(num_f), "# zero (avg)", "# zero (all {0})"
                                           .format(num_f), "# same (all {0})".format(num_f)]
        self.extra_stats["# illformed"] = str(average_list([get_num_dummies(drss)
                                              for drss in self.out_drss]))
        self.extra_stats["# perfect (avg)"] = str(average_list([get_num_for_score(idv,
                                                  check_score=1.0) for idv in self.idv_scores]))
        self.extra_stats["# zero (avg)"] = str(average_list([get_num_for_score(idv,
                                               check_score=0.0) for idv in self.idv_scores]))
        self.extra_stats["# perfect (all {0})".format(num_f)] = str(num_same_score(self.idv_scores,
                                                                    score_has_to_be=1.0))
        self.extra_stats["# zero (all {0})".format(num_f)] = str(num_same_score(self.idv_scores,
                                                                 score_has_to_be=0.0))
        self.extra_stats["# same (all {0})".format(num_f)] = str(num_same_score(self.idv_scores))

    def average_idv_multi(self):
        '''Average the list of X runs of an experiment for the 3 idv scores:
          match, prod, gold'''
        return_list = []
        for idx1 in range(len(self.multi_idv_scores[0])):
            new_list = []
            for idx2 in range(len(self.multi_idv_scores)):
                # Add the new list to the old list
                new_list.append(self.multi_idv_scores[idx2][idx1])
            # Now average the final list
            return_list.append(average_columns(new_list))
        return return_list

    def produce_counter_files(self, ident):
        '''Produce files that contain individual F-scores per DRS'''
        # Create new folder for the idv files
        new_folder = self.working_folder + ident + "/"
        mkdir(new_folder)
        extra_ext = ".log" if ident == "idv" else ""
        # Loop over out_files and run counter if necessary
        new_files = []
        for idx, out_file in enumerate(self.output_files):
            new_file = "{0}/{1}_{2}{3}".format(new_folder, self.prefix, ident, idx)
            if not os.path.isfile(new_file):
                # Hacky fix for having new file info only here
                extra_args = self.extra_args_dict[ident].replace('$NEW_FILE', new_file)
                run_counter(out_file, self.gold_drs_file, self.counter, self.sig_file,
                            new_file + extra_ext, self.threads, extra_args=extra_args)
            new_files.append(new_file)
        return new_files

    def avg_finegrained(self, counter_files, indicators, line_indices):
        '''Average a number of files that contain Counter fine-grained information'''
        eval_output = [load_sent_file(in_file) for in_file in counter_files]
        check_lines = []
        # Put the lines that we want to look at in single list of lists
        for idx1 in range(len(eval_output[0])):
            cur_lines = []
            for idx2 in range(len(counter_files)):
                cur_lines.append(eval_output[idx2][idx1])
            check_lines.append(cur_lines)
        # Now average those
        averaged_lines = []
        for lines in check_lines:
            averaged_lines.append(avg_nums_in_line(lines, 3))
        # From the average, extract the information that we want based on line number (hacky)
        return self.extract_finegrained_info(averaged_lines, indicators, line_indices)

    def extract_finegrained_info(self, lines, indicators, line_indices):
        '''From an averaged finegrained Counter file, extract all relevant numbers'''
        cur_dict = {}
        # Filter all lines that start with WARNING (not counting on those being in there)
        lines = [line for line in lines if not line.strip().startswith("WARNING")]
        # Save all the information in a dictionary
        for str_name, idx in zip(indicators, line_indices):
            cur_dict[str_name] = floats_in_line(lines[idx], only_take_first=True)
        # Save the items as well for easier access later
        cur_dict["items"] = indicators
        return cur_dict

    def add_layer_data(self):
        '''Read a file in CoNLL format that contains all layer information'''
        # Read in data, use functions from semtag_analysis
        # Now put the data in easily usable format
        # Save per layer, but also save everything
        self.all_layer_info = read_conll_data(self.layer_data)
        # This is a hardcoded list of layer information
        # We assume that the information is in this order in the CoNLL file
        self.layer_dict = {}
        for idx, layer in enumerate(self.layers):
            self.layer_dict[layer] = [[line[idx] for line in doc] for doc in self.all_layer_info]


def get_idv_differences(avg1, avg2):
    '''Return number of times model 1 > model 2, and ties, and other way around'''
    higher, ties, lower = 0, 0, 0
    for sc1, sc2 in zip(avg1, avg2):
        if sc1 > sc2:
            higher += 1
        elif sc1 == sc2:
            ties += 1
        else:
            lower += 1
    return higher, ties, lower


def create_stats_table(exp_list):
    '''Create a list of lists (table) for the counter fine information and the
       extra statistics we calculated for the two experiments'''
    print_divider()
    items, table = [], []
    # First add all the fine information from Counter
    # Loop over the result objects we saved in exp_list
    for idx, res in enumerate(exp_list):
        # Only add items once
        if idx == 0:
            items = res.avg_fine["items"][3:] + ["F1 std dev", "F1 conf interval"] \
                    + res.extra_stats["extra_stats"] \
                    + ["Prec def sense", "Rec def sense", "F1 def sense"]
        # The counter fine scores
        init_add = [res.avg_fine[item] for item in res.avg_fine["items"][3:]]
        # Also add std dev and conf interval that we saved separately in avg_exp_info
        init_add.append("{:.3f}".format(res.avg_exp_info.score_dict["F-score"][5]))
        init_add.append("-".join([str(sc) for sc in res.avg_exp_info.score_dict["F-score"][6]]))
        # Add the extra statistics
        for item in res.extra_stats["extra_stats"]:
            init_add.append(res.extra_stats[item])
        # Add the default-sense experiment statistics, Prec/rec/F1
        init_add.append(res.avg_sense["Prec"])
        init_add.append(res.avg_sense["Rec"])
        init_add.append(res.avg_sense["F1"])
        table.append(init_add)

    # Invert/transpose list
    table = transpose_list([items] + table)

    # If we have exactly two experiments, we can print some extra stats
    if len(exp_list) == 2:
        higher, ties, lower = get_idv_differences(exp_list[0].avg_idv_scores,
                                                  exp_list[1].avg_idv_scores)
        table.append(["# exp 1 > exp 2", str(higher), str(lower)])
        table.append(["# exp 1 == exp 2", str(ties), str(ties)])
    return table


def get_num_for_score(in_list, check_score):
    '''Return number of DRSs with a certain score (i.e. 1.0 or 0.0)'''
    return len([score for score in in_list if score == check_score])


def num_same_score(idv_list, score_has_to_be=-1):
    '''Return amount of DRSs that got the same score (out of 5 usually)
       If score_has_to_be >= 0, the scores has to be exactly that to count'''
    num = 0
    for idx1 in range(len(idv_list[0])):
        cur_items = []
        for idx2 in range(len(idv_list)):
            cur_items.append(idv_list[idx2][idx1])
        # Now check if we indeed count this one
        if len(set(cur_items)) == 1:
            if score_has_to_be >= 0.0:
                if cur_items[0] == score_has_to_be:
                    num += 1
            else:
                num += 1
    return num


def order_sents_by_fscore(idv_scores, sentences):
    '''Order the sentences based on the average idv_scores'''
    combined_list = [[round(idv, significant), sent, idx]
                     for idx, (idv, sent) in enumerate(zip(idv_scores, sentences))]
    # Now order the combined list based on the fscore
    ordered_list = sorted(combined_list, key=lambda x: x[0])
    return ordered_list


def run_counter(f1, f2, counter, sig_file, out_file, threads, extra_args="", do_print=True):
    '''Run Counter on two files, return results in a file'''
    call = "python {0} -f1 {1} -f2 {2} -g {3} {4} -ill dummy -p {5} > {6}" \
           .format(counter, f1, f2, sig_file, extra_args, threads, out_file)
    if do_print:
        print("Running counter, creating {0}".format(out_file))
    subprocess.call(call, shell=True)


def read_clause_file(in_file, avg_dic):
    '''Read in a Counter output file that contains F-scores per clause'''
    lines = load_sent_file(in_file)
    for line in lines[10:]:
        tab_line = [x.strip() for x in line.split('\t')]
        if len(tab_line) == 5 and tab_line[1].strip() != "F-score":  # skip header
            # We might want to rewrite a concept to it's synset ID to make sure
            # we do not miss concepts. This is because the Counter matching always returns
            # the originally produced concept, and not the synset
            clause_name = en_sense_dict[tab_line[0]] if tab_line[0] in en_sense_dict \
                          and is_concept(tab_line[0]) else tab_line[0]

            # Similarly, we also merge Role en RoleOf clauses, since Counter does so as well
            # Otherwise the Counter output of individual clause matching can give weird results
            if is_role(clause_name) and clause_name.endswith("Of") and len(clause_name) > 2:
                # Remove the Of from the name
                clause_name = clause_name[0:-2]

            # Add information to avg dic if we already saw it
            if clause_name in avg_dic:
                new_item = sum_two_lists(avg_dic[clause_name], [float(x) for x in tab_line[1:]])
                avg_dic[clause_name] = new_item
            else:
                avg_dic[clause_name] = [float(x) for x in tab_line[1:]]
    return avg_dic


def avg_clause_information(out_files, working_folder, gold_drs_file, counter, sig_file):
    '''Either read average file or create it by running counter multiple times and then averaging'''
    # Create avg clause file if they do not exist yet, always read in information
    threads = 8
    avg_dic = {}
    for idx, out_file in enumerate(out_files):
        cur_clause_file = working_folder + "avg_clause_file" + str(idx)
        if not os.path.isfile(cur_clause_file):
            run_counter(out_file, gold_drs_file, counter, sig_file,
                        cur_clause_file, threads, extra_args="-r 10 -ds 1")
        # Automatically keep track of average dictionary as well
        avg_dic = read_clause_file(cur_clause_file, avg_dic)
    # Give each value in avg_dic their new F-score
    for key in avg_dic:
        avg_dic[key] = avg_dic[key] + [compute_f(avg_dic[key][3], avg_dic[key][1],
                                       avg_dic[key][2], 3, True)]
    return avg_dic


def get_key_list(avg_clause_list, all_keys=[]):
    '''Get a list of all keys (clauses) we will be checking'''
    key_list = []
    for avg_clause in avg_clause_list:
        keys_and_gold = []
        for key in avg_clause:
            if not all_keys or key in all_keys:
                keys_and_gold.append([key, avg_clause[key][2]])
        sorted_keys = sorted(keys_and_gold, key=lambda x: x[1], reverse=True)
        for add_key in sorted_keys:
            if add_key[0] not in key_list:
                key_list.append(add_key[0])
    return key_list


def get_single_correct_clauses(all_items, names):
    '''Find clauses that were produced correctly for only a single experiment
       and not for all the other experiments. Sort by number of occurrence'''
    single_correct = start_dict_empty_list(names)
    for item in all_items:
        # If "NA" in the item that means that clause was not in gold,
        # so can never be produced correctly anyway
        if "NA" not in item[2:] and num_items_over_zero(item[2:]) == 1:
            # Add the item that is not zero, with number of occurences
            non_zero_idx = first_larger_than_zero_idx(item[2:])
            # Add a list with this information: name of clause, gold instances, F-score
            single_correct[names[non_zero_idx]].append([item[0], item[1], item[non_zero_idx + 2]])
    # Now we order the instances based on number of instances in gold, and then F-score
    # Save this in a list of lists that's already in nice printable format
    for key in single_correct:
        sorted_items = sorted(single_correct[key], key=lambda x: (x[1], x[2]), reverse=True)
        str_items = ["{0} ({1}, {2})".format(x[0], x[1], round(x[2], significant))
                     for x in sorted_items]
        single_correct[key] = str_items
    return single_correct


def create_clause_table(avg_clause_list, names, num_files):
    '''Create a table with F-scores per clause, order by gold instances and print per clause type'''
    all_items = []

    # First we want to get the order of items we will loop over
    # This so we can handle more than two experiments
    # Get all the keys from exp1 in order, than the keys from exp2 not in exp1,
    # then exp3 not in exp1 + exp2, etc
    key_list = get_key_list(avg_clause_list)

    # Loop over the clauses and save in general dict
    # Also keep track of clauses that were produced by one of the exps, but not the other
    all_items = []
    for key in key_list:
        add_item = [key]
        added_gold = False
        for avg_clause in avg_clause_list:
            if key in avg_clause:
                # Now add: key, gold inst, f-score1, fscore2, ..., etc
                # We divide gold_inst by the number of files here so it's correct again
                if not added_gold:
                    add_num = avg_clause[key][2]
                    if 0 < add_num < num_files:
                        raise ValueError("Impossible value of {0}".format(add_num))
                    add_item.insert(1, int(add_num / num_files))
                    added_gold = True
                add_item.append(avg_clause[key][4])
            else:
                # Item not present, F-score impossible to calculate, add "NA"
                add_item.append("NA")
        all_items.append(add_item)

    # Find the clauses that were correctly predicted by one of the experiments,
    # but never by any of the others (usually two)
    # Basically means that the exp has a score of > 0 for the clause, while the rest has 0
    single_correct = get_single_correct_clauses(all_items, names)
    return all_items, single_correct


def sum_scores_per_exp(exp_list, conc_key_list):
    '''Sum the match/prod/gold clauses per experiment, only for keys
       that are present in conc_key_list'''
    # Each exp start at 0
    res_comb = {}
    for res in exp_list:
        res_comb[res.name] = [0, 0, 0]

    # Loop over all keys, add scores per experiment
    total_gold = 0
    for c in conc_key_list:
        added_gold = False
        for res in exp_list:
            if c in res.avg_clause:
                # Sum prod, gold, match here
                res_comb[res.name] = sum_two_lists(res_comb[res.name], res.avg_clause[c][1:4])
                if not added_gold:
                    total_gold += res.avg_clause[c][2]
                    added_gold = True
    return res_comb, total_gold


def general_clause_analysis(exp_list, not_freq_conc):
    '''Analyse the performance on individual clauses. Print results in a nice table'''
    names = [res.name for res in exp_list]
    # Create a sorted table with the F-scores of all experiments, ordered by number of gold clauses
    all_items, single_correct = create_clause_table([res.avg_clause for res in exp_list],
                                                    [res.name for res in exp_list],
                                                    exp_list[0].num_files)
    # Now create individual tables for operators, roles and concepts
    op_table = sorted([a for a in all_items if is_operator(a[0])], key=lambda x: x[1], reverse=True)
    role_table = sorted([a for a in all_items if is_role(a[0])], key=lambda x: x[1], reverse=True)
    con_table = sorted([a for a in all_items if is_concept(a[0])], key=lambda x: x[1], reverse=True)

    # Create a table for all concepts that are not the most frequent sense
    conc_to_match = [nfc[0] + '.' + nfc[1].replace('"', '') for nfc in not_freq_conc]
    not_freq_conc_table = sorted([a for a in all_items if is_concept(a[0]) and a[0]
                                  in conc_to_match], key=lambda x: x[1], reverse=True)
    # Combine all items for non-frequent concepts
    conc_key_list = get_key_list([res.avg_clause for res in exp_list], conc_to_match)
    res_comb, total_gold = sum_scores_per_exp(exp_list, conc_key_list)

    # Create final combined item
    item = ["Combined", int(total_gold / exp_list[0].num_files)] + [compute_f(res_comb[res.name][2],
            res_comb[res.name][0], res_comb[res.name][1], significant=significant, f_only=True)
            for res in exp_list]

    # Only keep the ones that occur more than X times in the gold data
    pr_lim = 5
    hdr = ["Clause", "Gold inst"] + names

    # Create the tabbed tables and print immediately
    print("Comparison of individual operator scores:\n")
    for line in create_tab_list([hdr] + [x for x in op_table if x[1] >= pr_lim], [], table_sep):
        print(line)
    print_divider()
    print("Comparison of individual role scores:\n")
    for line in create_tab_list([hdr] + [x for x in role_table if x[1] >= pr_lim], [], table_sep):
        print(line)
    print_divider()
    print("Comparison of individual concept scores:\n")
    for line in create_tab_list([hdr] + [x for x in con_table if x[1] >= pr_lim], [], table_sep):
        print(line)
    print_divider()
    print("F-scores on concepts that were not the most frequent in given DRS set:\n")
    for line in create_tab_list([hdr] + [item] + not_freq_conc_table, [], table_sep):
        print(line)

    # Print the clauses correctly produced by a certain experiment
    # that were never produced in the other experiments
    if len(names) > 1:
        print_divider()
        for key in single_correct:
            print("\nClauses correctly done by {0}, but not by other exps ({1}):\n"
                  .format(key, len(single_correct[key])))
            print(", ".join(single_correct[key]))
    return all_items


def worst_sentences_analysis(avg_idv_scores1, avg_idv_scores2, sentences, ret_items, names):
    '''Do analysis on which sentences were the hardest for the two models'''
    print_divider()
    # First simply order the sentences based on their avg F-score
    ordered_sentences1 = order_sents_by_fscore(avg_idv_scores1, sentences)
    ordered_sentences2 = order_sents_by_fscore(avg_idv_scores2, sentences)
    # And print the worst X
    print("{0} worst sentences for {1}:\n".format(ret_items, names[0]))
    for idx in range(len(ordered_sentences1[0:ret_items])):
        print(ordered_sentences1[idx][0], ordered_sentences1[idx][1])
    print_divider()
    print("{0} worst sentences for {1}:\n".format(ret_items, names[1]))
    for idx in range(len(ordered_sentences2[0:ret_items])):
        print(ordered_sentences2[idx][0], ordered_sentences2[idx][1])
    # Print the overlap in number of worst sentences out of e.g. 5, 10, 20.
    # Gives an indication how similar experiments are
    print_divider()
    print("Analysis of overlap between worst sentences:\n")
    check_range = [5, 10, 20, 50, 100]
    for num in check_range:
        num_matching = num_common_elements([item[2] for item in ordered_sentences1[0:num]],
                                           [item[2] for item in ordered_sentences2[0:num]])
        print("{0} of the {1} worst sentences were the same".format(num_matching, num))


def create_senlen_plot(score_list, tokenized_sentences, min_occurrence,
                       min_sen_len, output_file, names):
    '''Create an F-score over sentence length plot for two experiments'''
    print_divider()
    # Get all the sentence length from tokenized file
    sen_lengths = [len(x.split()) for x in load_sent_file(tokenized_sentences)]
    # Get the maximum based on the minimum of sentences that should have that length
    max_sen_len = get_max_sen_len(sen_lengths, min_occurrence)
    # Average the F-scores per sentence length
    avg_scores, length_counts, sen_range = avg_per_length(score_list, sen_lengths,
                                                          min_sen_len, max_sen_len)
    # Create the final plot
    print("Created sentence length plot: {0}".format(output_file))
    make_plot(avg_scores, names, sen_range, output_file, num_sents=length_counts)


def idv_avg_clause_info(cur_drss, working_dir, exp_ident, out_file_root,
                        gold_drs_file, counter, sig_file):
    '''Similar to avg clause information but then for the individual DRS analysis'''
    avg_dic = {}
    threads = 8
    for drs_idx in range(0, len(cur_drss)):
        cur_clause_file = working_dir + "cur_avg" + str(exp_ident) + "_" + str(drs_idx)
        # Always run Counter since we reuse file names
        run_counter("{0}{1}".format(out_file_root, drs_idx), gold_drs_file, counter, sig_file,
                    cur_clause_file, threads, extra_args="-r 10 -ds 1", do_print=False)
        # Automatically keep track of average dictionary as well
        avg_dic = read_clause_file(cur_clause_file, avg_dic)
    # Give each value in avg_dic their new F-score
    for key in avg_dic:
        avg_dic[key] = avg_dic[key] + [compute_f(avg_dic[key][3], avg_dic[key][1],
                                                 avg_dic[key][2], 3, True)]
    return avg_dic


def individual_clause_analysis(sorted_diffs, working_dir, gold_drss, sentences, out_drss1,
                               out_drss2, counter, sig_file, indices, names):
    '''Do a more detailed analysis to figure out why some DRSs are so much better than the other'''
    header = [["Clause", "Gold inst"] + names]
    # Loop over the indices that we want to check
    for in_idx in indices:
        print_divider()
        # Get the sorted_diffs index that we will be using
        idx = sorted_diffs[in_idx][0]
        # Select the gold_drs, sentence and output_files we will be working with
        cur_drss1 = [drss[idx] for drss in out_drss1]
        cur_drss2 = [drss[idx] for drss in out_drss2]
        cur_gold_drs = gold_drss[idx]
        cur_sent = sentences[idx]
        # We have to write these to a file to make it work with the other functions
        for i in range(len(cur_drss1)):
            write_to_file(cur_drss1[i], "{0}out_drs1_{1}".format(working_dir, i))
            write_to_file(cur_drss2[i], "{0}out_drs2_{1}".format(working_dir, i))
        # Also write the single gold drs
        write_to_file(cur_gold_drs, "{0}gold_drs".format(working_dir))
        # Get the averaged dictionaries
        avg_dict1 = idv_avg_clause_info(cur_drss1, working_dir, "1", working_dir + "out_drs1_",
                                        working_dir + "gold_drs", counter, sig_file)
        avg_dict2 = idv_avg_clause_info(cur_drss2, working_dir, "2", working_dir + "out_drs2_",
                                        working_dir + "gold_drs", counter, sig_file)
        # Get the tables
        all_items, _ = create_clause_table([avg_dict1, avg_dict2], names, len(cur_drss1))
        print("\nDetailed scores for largest diff DRS {0} (idx {1}) - avged over {2} files \
               \nSentence: {3}\n".format(in_idx, idx, len(out_drss1), cur_sent))
        # Print gold DRS and examples of the output (not all)
        print("Gold DRS:\n")
        print_drs(cur_gold_drs)
        # Don't print "example" if we have only one output file
        print_line = "Example output for" if len(out_drss1) > 1 else "Output for"
        print("{0} {1}:\n".format(print_line, names[0]))
        print_drs(cur_drss1[0])
        print("{0} {1}:\n".format(print_line, names[1]))
        print_drs(cur_drss2[0])
        # Print the all items table, sorted by number of gold instances and F-score
        for line in create_tab_list(header + [[str(y) for y in x]
                                    for x in all_items], [], table_sep):
            print(line)


def create_and_write_stats_file(exp_list, tok_sents_file, stats_file):
    '''Write averaged statistics per sentence to a stats file
       so we can use R to do statistics later'''
    # Also order of what information is added
    data = [["sid", "parser", "sen-len", "prod-clauses",
             "gold-clauses", "match-clauses", "F-score"]]
    tok_lens = [len(x.split()) for x in load_sent_file(tok_sents_file)]
    # Loop over instances and experiments to save data lines
    for idx in range(len(exp_list[0].avg_idv_scores)):  # Contains match, prod, gold
        for res in exp_list:
            data.append([idx, res.name, tok_lens[idx]] + res.avg_idv_scores[idx]
                        + [res.avg_idv_fscores[idx]])
    write_to_file([",".join([str(x) for x in line]) for line in data], stats_file)


def print_comparison_tables(exp_list, not_freq_conc):
    '''Print all tables for the information per experiment (Counter F-scores, tag scores, etc)'''
    # First create a table with all counter scores (avg etc) and the new statistics, and print it
    counter_fine_table = create_stats_table(exp_list)
    tabbed_table = create_tab_list([[""] + [res.name for res in exp_list]] + counter_fine_table,
                                   [], table_sep)
    print_list(tabbed_table, leading_newline=True, ending_newline=True, strip_line=False)

    # Analysis based on the different clause types (e.g. how well do we score on negation)
    print_divider()
    all_items = general_clause_analysis(exp_list, not_freq_conc)
    return all_items


def get_not_most_freq_sense_concepts(drss):
    '''Get all glosses that are not the most frequent sense in the gold set'''
    conc_dict = {}
    # Create a dictionary that for each word lists all the senses
    for drs in drss:
        for clause in drs:
            if not clause.strip().startswith('%') and is_concept(clause.split()[1]):
                concept, sense = clause.split()[1], clause.split()[2]
                if concept in conc_dict:
                    conc_dict[concept].append(sense)
                else:
                    conc_dict[concept] = [sense]
    # Loop over the dict, save all conc + sense that is not the most frequent
    # If there's a tie, we don't add any
    conc_list = []
    for conc in conc_dict:
        most_common_value = most_common(conc_dict[conc])
        most_common_count = conc_dict[conc].count(most_common_value)
        for sns in set(conc_dict[conc]):
            # This way we also filter out ties
            if conc_dict[conc].count(sns) < most_common_count:
                conc_list.append([conc, sns, conc_dict[conc].count(sns)])
    sorted_concs = sorted(conc_list, key=lambda x: x[2], reverse=True)
    return sorted_concs


def best_worst_diff_between_exps(names, all_items, return_items):
    '''Calculate the best and worst performance on specific clauses, relatively for the experiments.
       Order them based on the difference. Only return the Top N.'''
    header = ["Clause", "Gold inst"] + names + ["Diff"]
    # Number of times a clause should be in gold standard before it gets added in the table
    comparison_limit = 10
    # Sort the all items table based on the difference in F-scores
    all_items_sorted = sorted([item + [round(item[2] - item[3], significant)] for item in all_items
                              if "NA" not in [item[2], item[3]]], key=lambda x: x[4], reverse=True)

    # For exp1 > exp2, print difference
    print_divider()
    print("Clauses for which {0} > {1} has the most difference:\n".format(names[0], names[1]))
    for line in create_tab_list([header] + [x for x in all_items_sorted
                                if x[1] >= comparison_limit][0:return_items], [], table_sep):
        print(line)
    # For exp2 > exp1 as well
    print("\nClauses for which {0} > {1} has the most difference:\n".format(names[1], names[0]))
    for line in create_tab_list([header] + [[str(y) for y in x] for x in all_items_sorted
                                if x[1] >= comparison_limit][::-1][0:return_items], [], table_sep):
        print(line)


def print_idv_analysis(sorted_diffs, sentences, limit):
    '''Print some statistics and analysis for the comparison of individual DRSs'''
    # Simply print the sentences with the most difference, both top and bottom
    print("\nSentences for which exp1 has most positive difference with exp2:\n")
    for srt in sorted_diffs[0:limit]:
        print(srt[0], srt[1], sentences[srt[0]])
    print("\nSentences for which exp1 has most negative difference with exp2:\n")
    for srt in sorted_diffs[len(sorted_diffs) - limit:][::-1]:
        print(srt[0], srt[1], sentences[srt[0]])


def compare_idv_scores(idv_scores1, idv_scores2, out_drss1, out_drss2):
    '''Compare the individual scores to select relative best/worst sentences'''
    # Get list of indices that contain invalid DRS (we don't count those)
    invalid_indices = get_invalid_indices(out_drss1 + out_drss2)

    # Loop over files and calculate difference
    # If invalid idx, give difference of 0 so we never use it for something
    all_diffs = []
    for sent_idx in range(len(idv_scores1[0])):
        if sent_idx not in invalid_indices:
            # Get the two lists of scores
            scores1 = [idv_scores1[file_idx][sent_idx] for file_idx in range(len(idv_scores1))]
            scores2 = [idv_scores2[file_idx][sent_idx] for file_idx in range(len(idv_scores2))]
            # Get the difference between them
            diff = average_difference(scores1, scores2, do_round=3)
            all_diffs.append([sent_idx, diff, scores1, scores2])
        else:
            diff = 0
            all_diffs.append([sent_idx, diff, [], []])
    # Now sort the difference in descending order, so we can select top/bottom X later
    return sorted(all_diffs, key=lambda x: x[1], reverse=True)


def do_specific_comparison(args, exp_list, all_items):
    '''Do a specific comparison between two experiments (so no long tables).
       For example check which sentences had the best/worst relative performance.
       Also do statistical tests and compare individual DRSs'''
    names = [res.name for res in exp_list]
    # We need the gold DRSs + sentences
    gold_drss = get_drss(args.dev_drss)
    sentences = load_sent_file(args.sentences)

    # We are interested in the best and worst differences for individual clause F-scores
    # First we need to add a column with difference in F-score to all_items, afterwards sort by it
    best_worst_diff_between_exps(names, all_items, args.ret)

    # Do statistical analysis (approximate randomization)
    print_divider()
    print("Do statistical testing with approximate randomization ({0} runs)\n"
          .format(args.randomizations))
    p_value1 = sign_test(flatten_list_of_list(exp_list[0].idv_scores),
                         flatten_list_of_list(exp_list[1].idv_scores), args.randomizations)
    p_value2 = sign_test(flatten_list_of_list(exp_list[1].idv_scores),
                         flatten_list_of_list(exp_list[0].idv_scores), args.randomizations)
    print("{0} better than {1}: p-value of {2}".format(names[0], names[1], round(p_value1, 5)))
    print("{0} better than {1}: p-value of {2}".format(names[1], names[0], round(p_value2, 5)))

    # Do analysis on which sentences were the hardest for the two models
    worst_sentences_analysis(exp_list[0].avg_idv_fscores, exp_list[1].avg_idv_fscores,
                             sentences, args.ret, names)

    # Analysis of which DRSs especially improved/decreased in F1-score between the experiments
    print_divider()
    sorted_diffs = compare_idv_scores(exp_list[0].idv_scores, exp_list[1].idv_scores,
                                      exp_list[0].out_drss, exp_list[1].out_drss)

    # Print some analysis
    print_idv_analysis(sorted_diffs, sentences, args.ret)

    # Now do a more detailed analysis for the top X DRSs if we want
    # We are mostly interested in the matching/nonmatching clauses of the produced DRSs
    # Use the functions from worst_sentences_analysis to check that using Counter
    if args.analyse_indices:
        analysis_dir = args.working + 'idv_analysis/'
        mkdir(analysis_dir)
        # Analyse for which exp1 > exp2
        individual_clause_analysis(sorted_diffs, analysis_dir, gold_drss, sentences,
                                   exp_list[0].out_drss, exp_list[1].out_drss, args.counter,
                                   args.sig_file, args.analyse_indices, names)
        # Analysis for which exp2 > exp1
        individual_clause_analysis(sorted_diffs, analysis_dir, gold_drss, sentences,
                                   exp_list[1].out_drss, exp_list[0].out_drss, args.counter,
                                   args.sig_file, args.analyse_indices, names)


def get_exp_information(args, names):
    '''Load/create all information per experiment that we specified'''
    exp_list = []
    for idx, in_folder in enumerate(args.folders):
        # Create a working folder for this experiment
        cur_dir = args.working + names[idx] + '/'
        mkdir(cur_dir)
        # Then load the experiment files in object
        res = Results(in_folder, args.prefix, names[idx], args.drs_ext, cur_dir, args.dev_drss,
                      args.counter, args.threads, args.sig_file, args.layer_data)
        res.create_result_files()
        # Save this info dict for comparison later
        exp_list.append(res)
    return exp_list


def main():
    '''Main function of drs_jury'''
    args = create_arg_parser()
    # Set some variables that we don't want to pass along to all functions
    global wait_for_input, significant, table_sep
    wait_for_input = args.wait_for_input
    significant = args.significant
    table_sep = ' & ' if args.latex else '\t'
    names = args.names if args.names else ["Exp{0}".format(idx) for idx in range(len(args.folders))]

    # Get list of concepts that are not the most frequent sense in the DRS set
    train_drss = get_drss(args.train_drss)
    not_most_freq_sense = get_not_most_freq_sense_concepts(train_drss)

    # Important step: load/create all files per experiment that we load in an Results object
    exp_list = get_exp_information(args, names)

    # Print tables with all information, save all_items result because we need it later
    all_items = print_comparison_tables(exp_list, not_most_freq_sense)

    # Now do experiments based on tags, in this case semtags
    # For example, print an F-score for all sentences that contained the "CON" semtag
    if args.layer_data:
        print_divider()
        single_list = single_tag_analysis(exp_list[0].layer_dict["sem"],
                                          [res.avg_idv_scores for res in exp_list],
                                          args.min_occurrence, True)
        for line in create_tab_list([["Tag", "Docs"] + names] + single_list,
                                   "\nResults for sentences that contain individual tags:\n", "\t"):
            print(line)
        # Do the analysis for the combined semtag experiment (negation, numerals, modals, etc)
        print_divider()
        combined_list = combined_tag_analysis(exp_list[0].layer_dict["sem"],
                                              [res.avg_idv_scores for res in exp_list],
                                              get_semtag_exps(), True)
        for line in create_tab_list([["Exp", "Docs"] + names] + combined_list,
                                    "\nResults semtag experiment:\n", "\t"):
            print(line)

    # Print a sentence length plot. This is what we need the tokenized input for
    output_file = args.output_file if args.output_file else args.working + 'senlen_plot.pdf'
    create_senlen_plot([res.avg_idv_fscores for res in exp_list], args.tokenized_sentences,
                       args.min_occurrence, args.min_sen_len, output_file, names)

    # Print some stats to a stats file, if we specified it. Can be useful if you want to do
    # statistical analysis in R or some other software
    if args.stats_file and args.tokenized_sentences:
        create_and_write_stats_file(exp_list, args.tokenized_sentences, args.stats_file)
        print_divider()
        print("Created stats file in csv format: {0}".format(args.stats_file))

    # If we have exactly two input folders we do some more analysis
    if len(names) == 2:
        do_specific_comparison(args, exp_list, all_items)


if __name__ == "__main__":
    main()
