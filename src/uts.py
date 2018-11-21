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

### Settings

op_boxes = ['NOT', 'POS', 'NEC', 'IMP', 'DIS', 'PRP', 'DRS', 'ANSWER', 'PARALLEL', 'CONTINUATION', 'CONTRAST', 'RESULT', 'EXPLANATION', 'DUP']

### Functions

def is_role(string):
	'''Check if string is in the format of a role'''
	return string[0].isupper() and any(x.islower() for x in string[1:]) and all(x.islower() or x.isupper() or x == '-' for x in string)

def write_to_file(lst, file_new):
    '''Write list to file'''
    out_f = codecs.open(file_new, "w", "utf-8")
    for line in lst:
        try:
            out_f.write(line.strip().decode('utf-8', 'ignore') + '\n')
        except:
            print line  
    out_f.close()


def write_list_of_lists(lst, f, new_line=True):
    '''Write lists of lists to file'''
    out_f = codecs.open(f, "w", "utf-8")
    for ls in lst:
        for l in ls:
            out_f.write(l.strip().decode('utf-8', 'ignore') + '\n')
        if new_line:
            out_f.write('\n')
    out_f.close()        


def get_files_in_folder(f):
    '''Gets all files in a folder'''
    return [f for f in os.listdir('.') if os.path.isfile(f)]


def average(l, roud_by=4):
    '''Take average of list of numbers'''
    return round((float(sum(l)) / float(len(l))),round_by)


def get_files_in_folder_by_ext(folder, ext):
    '''Gets all files in current folder if they have certain extension'''
    return [f for f in os.listdir(folder) if os.path.isfile(f) and f.endswith(ext)]


def get_drss(f, amr_input=False):
    '''Read and return individual DRSs in clause format'''
    cur_drs  = []
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


def load_json_dict(d):
    '''Funcion that loads json dictionaries'''

    with open(d, 'r') as in_f:
        dic = json.load(in_f)
    in_f.close()
    return dic


def get_direct_subfolders(a_dir):
    return [name for name in os.listdir(a_dir)
            if os.path.isdir(os.path.join(a_dir, name))]


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


def all_lower(string):
    '''Checks if all items in a string are lowercase'''
    return all(x.islower() for x in string)


def between_quotes(string):
    '''Return true if a value is between quotes'''
    return (string.startswith('"') and string.endswith('"')) or (string.startswith("'") and string.endswith("'"))


def print_sorted_dict(d, reverse=True, maximum = 0):
    '''Function that prints a sorted dictionary'''
    counter = 0
    for w in sorted(d, key=d.get, reverse=reverse):
        if counter <= maximum and maximum != 0:
            print (w, d[w])
            counter += 1


def add_to_dict(d, key):
    '''Function to add key to dictionary'''
    if key in d:
        d[key] += 1
    else:
        d[key] = 1

    return d
