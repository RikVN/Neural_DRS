#!/usr/bin/env python
# -*- coding: utf8 -*-

'''General utils'''

from collections import defaultdict
import sys
import re
import os
import time
from random import shuffle
import json
import codecs
import subprocess

### Settings

op_boxes = ['ALTERNATION', 'ATTRIBUTION', 'BACKGROUND', 'COMMENTARY', 'CONDITION', 'CONSEQUENCE', 'CONTINUATION', 'CONTRAST', 'DIS', 'DUP', 'ELABORATION', 'EXPLANATION', 'IMP', 'INSTANCE', 'NARRATION', 'NEC', 'NECESSITY', 'NEGATION', 'NOT', 'PARALLEL', 'POS', 'POSSIBILITY', 'PRECONDITION', 'PRESUPPOSITION', 'RESULT', 'TOPIC']

### Functions

def write_to_file(lst, out_file):
    '''Write list to file'''
    with open(out_file, "w") as out_f:
        for line in lst:
            out_f.write(line.strip() + '\n')
    out_f.close()


def most_common(lst):
    '''Return most common item in a list'''
    return max(set(lst), key=lst.count)


def write_list_of_lists(lst, out_file, extra_new_line=True):
    '''Write lists of lists to file'''
    with open(out_file, "w") as out_f:
        for sub_list in lst:
            for item in sub_list:
                out_f.write(item.strip() + '\n')
            if extra_new_line:
                out_f.write('\n')
    out_f.close()


def write_list_of_lists_of_lists(lst, out_file, extra_new_line=True):
    '''Write list of lists of lists to file'''
    with open(out_file, "w") as out_f:
        for sub_list in lst:
            for item in sub_list:
                for line in item:
                    out_f.write(line.strip() + '\n')
                if extra_new_line:
                    out_f.write('\n')
            if extra_new_line:
                out_f.write('\n')
    out_f.close()


def pickle_object(l, out_file):
    with open(out_file, "wb") as fp:
        pickle.dump(l, fp)
    fp.close()


def unpickle_object(in_file):
    with open(in_file, "rb") as fp:
        l = pickle.load(fp)
    fp.close()
    return l


def get_files_in_folder(folder):
    '''Gets all files in a folder'''
    return [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]


def average(l, round_by=4):
    '''Take average of list of numbers'''
    return round((float(sum(l)) / float(len(l))), round_by)


def average_list(in_list):
    '''From a list of numbers, return the average'''
    return float(sum(in_list)) / float(len(in_list))


def get_files_in_folder_by_ext(folder, ext):
    '''Gets all files in current folder if they have certain extension'''
    return [f for f in os.listdir(folder) if os.path.isfile(f) and f.endswith(ext)]


def get_drss(f, amr_input=False):
    '''Read and return individual DRSs in clause format'''
    cur_drs = []
    all_drss = []

    for line in open(f, 'r'):
        if not line.strip():
            if cur_drs:
                all_drss.append(cur_drs)
                cur_drs = []
        else:
            if amr_input:
                cur_drs.append(line.rstrip())
            else:
                cur_drs.append(line.strip())
    ## If we do not end with a newline we should add the DRS still
    if cur_drs:
        all_drss.append(cur_drs)

    return all_drss


def drs_string_to_list(drs):
    '''Change a DRS in string format (single list) to a list of lists
       Also remove comments from the DRS'''
    drs = [x for x in drs if x.strip() and not x.startswith('%')]
    drs = [clause.split()[0:clause.split().index('%')] if '%' in clause.split() else clause.split() for clause in drs]
    return drs


def print_both(string, f):
    '''Function to print both screen and to file'''
    print (string)
    if f:
        f.write(string + '\n')


def get_files_by_ext(direc, ext):
    '''Function that traverses a directory and returns all files that match a certain extension'''

    return_files = []
    for root, _, files in os.walk(direc):
        for f in files:
            if f.endswith(ext):
                return_files.append(os.path.join(root, f))

    return return_files


def get_files_in_folder_by_ext(folder, ext):
    '''Gets all files in current folder if they have certain extension'''
    return [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f)) and f.endswith(ext)]


def get_files_by_ext(direc, ext):
    '''Function that traverses a directory and returns all files that match a certain extension'''
    return_files = []
    for root, dirs, files in os.walk(direc):
        for f in files:
            if f.endswith(ext):
                return_files.append(os.path.join(root, f))
    return return_files


def flatten_list_of_list(l):
    '''Flatten a list of lists'''
    return [item for sublist in l for item in sublist]


def list_to_dict(l):
    '''Change list to dictionary with value 1, makes searching faster'''
    d = {}
    for item in l:
        d[item] = 1
    return d

def print_drs(drs, remove_comments=True, extra_newline=True):
    '''Print a DRS (list of lists), remove lines that are comments as default'''
    for clause in drs:
        if clause.strip() and (not clause.strip().startswith('%') or not remove_comments):
            print (clause.strip())
    if extra_newline:
        print()


def load_json_dict(d):
    '''Funcion that loads json dictionaries'''
    with open(d, 'r') as in_f:
        dic = json.load(in_f)
    in_f.close()
    return dic


def json_by_line(input_file):
    '''Read input file which is a file of json objects'''
    data = []
    with open(input_file, 'r') as f:
        for line in f:
            data.append(json.loads(line))
    return data


def current_time():
    return time.ctime()


def is_dummy(drs):
    '''Function that return true if DRS is a dummy (alwayswrong)'''
    for clause in drs:
        if 'alwayswrong' in clause:
            return True
    return False


def get_direct_subfolders(a_dir):
    '''Get the direct subfolders of a certain folder (so not recursive)'''
    return [name for name in os.listdir(a_dir)
            if os.path.isdir(os.path.join(a_dir, name))]


def get_part_doc(line):
    part = re.findall(r'\p(\d\d)/', line)[0]
    doc = re.findall(r'd(\d\d\d\d)/', line)[0]
    return part, doc


def save_json_dict(data, file_name):
    '''Function that saves json dictionary'''
    with open(file_name, 'w') as fp:
        json.dump(data, fp)


def remove_empty(l):
    '''Function that removes empty values from list'''
    return [x for x in l if x]


def all_upper(string):
    '''Checks if all items in a string are uppercase'''
    return all(x.isupper() for x in string)


def is_operator(string):
    '''Checks if all items in a string are uppercase'''
    return all(x.isupper() or x.isdigit() for x in string) and string[0].isupper()


def is_role(string):
    '''Check if string is in the format of a role'''
    return string[0].isupper() and any(x.islower() for x in string[1:]) and all(x.islower() or x.isupper() or x == '-' for x in string)


def all_lower(string):
    '''Checks if all items in a string are lowercase'''
    return all(x.islower() for x in string)


def is_concept(string):
    '''Return true is the string looks like a DRS concept'''
    return not is_role(string) and not is_operator(string)


def between_quotes(string):
    '''Return true if a value is between quotes'''
    return (string.startswith('"') and string.endswith('"')) or (string.startswith("'") and string.endswith("'"))


def is_punct(string):
    '''Check if string is punctuation for which we do nothing'''
    return not(any(x.isalpha() for x in string) or any(x.isdigit() for x in string))


def print_sorted_dict(d, reverse=True, maximum=0):
    '''Function that prints a sorted dictionary'''
    counter = 0
    for w in sorted(d, key=d.get, reverse=reverse):
        if counter <= maximum and maximum != 0:
            print(w, d[w])
            counter += 1

def error_if_not_exists(input_file):
    '''Raise error if file does not exist'''
    if not os.path.isfile(input_file):
        raise ValueError("Input file {0} does not exist".format(input_file))


def mkdir(dr):
    '''Create directory if not exists'''
    subprocess.call("mkdir -p {0}".format(dr), shell=True)


def delete_if_exists(path):
    try:
        os.unlink(path)
    except OSError:
        pass


def count_lines_in_file(path):
    result = 0
    with open(path, 'r') as f:
        for line in f:
            result += 1
    return result


def makedirs(path):
    try:
        os.makedirs(path)
    except OSError:
        raise ValueError("Problem making dir")

def copy_file(f1, f2):
    '''Copy file f1 to location f2'''
    subprocess.call("cp {0} {1}".format(f1, f2), shell=True)


def is_non_zero_file(fpath):
    return os.path.isfile(fpath) and os.path.getsize(fpath) > 0


def get_first_arg_boxes(clf):
    '''Return all boxes in a DRS based on the first argument'''
    boxes = []
    for c in clf:
        if c[0] not in boxes:
            boxes.append(c[0])
    return boxes

def remove_by_first_arg_box(clf, box):
    '''Remove all clauses that contain a certain box as first arg
       Might help solving subordinate relation loop problems'''
    return [x for x in clf if x[0] != box]

def powerset(s):
    '''Given a set, return the powerset
    Remove items of length < 2 and > 5 and sort by size (ascending)
    https://stackoverflow.com/questions/1482308/how-to-get-all-subsets-of-a-set-powerset'''
    x = len(s)
    lst = []
    for i in range(1 << x):
        # Don't do ridicoulus amounts
        if len(lst) > 5000:
            break
        lst.append([s[j] for j in range(x) if i & (1 << j)])
    l = [x for x in lst if len(x) > 1]
    l.sort(key=len)
    return l


def add_to_dict(d, key):
    '''Function to add key to dictionary'''
    if key in d:
        d[key] += 1
    else:
        d[key] = 1

    return d


def print_list(in_list, leading_newline=False, ending_newline=False, strip_line=True):
    '''Print each item in a list, with leading/ending newline or not'''
    if leading_newline:
        print ()
    for line in in_list:
        if strip_line:
            print (line.strip())
        else:
            print (line)
    if ending_newline:
        print ()

def num_common_elements(list1, list2):
    '''Return number of elements in list1 that are also in list2.'''
    return len(set(list1).intersection(list2))

def sum_two_lists(list1, list2):
    '''Sum the contents of two lists and return'''
    return [a + b for a, b in zip(list1, list2)]

def load_idv_scores(file_list):
    '''Load al individual scores for all file in a list'''
    return [[float(x.strip()) for x in open(in_file, 'r')] for in_file in file_list]


def load_multi_idv_scores(file_list):
    '''Load al individual scores for all file in a list'''
    return [[[float(y) for y in x.split()] for x in open(in_file, 'r')] for in_file in file_list]


def load_sent_file(in_file):
    '''Simply read a file and strip the input sentences'''
    return [x.strip() for x in open(in_file, 'r')]


def floats_in_line(line, only_take_first=False):
    '''Return all floats in the line as a list, except if there's only one item'''
    floats = re.findall(r'[\d]+\.[\d]+', line)
    if not floats:
        raise ValueError("No number found in line:", line)
    elif len(floats) == 1 or only_take_first:
        return float(floats[0])
    else:
        return [float(sc) for sc in floats]

def get_num_dummies(drss):
    '''Return the number of dummies for a list of DRSs'''
    dummies = 0
    for drs in drss:
        if is_dummy(drs):
            dummies += 1
    return dummies


def remove_comments(clause):
    '''Remove all comments, e.g. all text after % character'''
    return clause.split()[0:clause.split().index('%')] if '%' in clause.split() else clause.split()


def num_items_over_zero(in_list):
    '''For a given list, return the number of numbers that are > 0'''
    return len([x for x in in_list if x > 0])


def first_larger_than_zero_idx(in_list):
    '''Return the idx of the first number that is larger > 0'''
    for idx, value in enumerate(in_list):
        if value > 0:
            return idx
    raise ValueError("No value > 0 found in this list:\n{0}".format(in_list))


def start_dict_empty_list(key_list):
    '''Start a dictionary with an empty list for each string in key_list'''
    dic = {}
    for key in key_list:
        dic[key] = []
    return dic


def read_and_strip_file(f):
    '''Read file and strip each line'''
    return [x.strip() for x in open(f, 'r')]


def remove_doubles_in_order(in_list):
    '''Remove double items in a list, but keep initial order'''
    new_list = []
    for item in in_list:
        if item not in new_list:
            new_list.append(item)
    return new_list


def voc_to_tok(in_list, vocab):
    '''Convert list of indices to tokens, stop after @end@ token is predicted'''
    tokens = []
    end_idx = [idx for idx, y in enumerate(vocab) if y == "@end@"][0]
    for num in in_list:
        find_num = int(num) - 1
        if find_num == end_idx: #found ending token
            return tokens
        tokens.append(vocab[find_num])
    return tokens


def read_allennlp_json_predictions(input_file, vocab, min_tokens):
    '''Read the json predictions of AllenNLP
       Bit tricky: if predictions for the winning beam are very short we take a later prediction and
       ignore the "winning" beam. Label smoothing can have this side effect that cuts the sequences
       short otherwise. We need the vocab for that. Raise error if we did not specify a vocab to help us
       remember this issue'''
    vocab = read_and_strip_file(vocab)
    dict_lines = json_by_line(input_file)
    lines = []
    for i, dic in enumerate(dict_lines):
        tokens = dic["predicted_tokens"]
        if len(tokens) >= min_tokens:
            lines.append(" ".join(tokens))
        # Not enough tokens in output, go down beam search and take first one that is long enough
        # If all not long enough, take longest one
        else:
            predictions = dic["predictions"][1:]
            found = 0
            cur_pred = tokens
            for idx, pred in enumerate(predictions):
                cur_tok = voc_to_tok(pred, vocab)
                if len(cur_tok) >= min_tokens:
                    # We found a line that's long enough, return that
                    lines.append(" ".join(cur_tok))
                    found = idx + 2
                    break
                elif len(cur_tok) > len(cur_pred):
                    # Line not long enough, but might be longer than first, so keep just in case
                    cur_pred = cur_tok
                    found = idx + 2
            else:
                # Did not break out of for-loop, add cur_pred to lines
                lines.append(" ".join(cur_pred))

            # Print output for logging
            if found == 0:
                print("DRS {0}: first beam answer too short but still used".format(i))
            else:
                print("DRS {0}: first beam answer too short, use beam {1} instead".format(i, found))
    return lines
