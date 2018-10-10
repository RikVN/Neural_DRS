#!/usr/bin/env python
# -*- coding: utf8 -*-

'''
Script that preprocess DRS-clause files and puts them in a format for sequence-to-sequence algorithms
Example usage (python2): python preprocess.py -i INPUT_FILE -s SENT_FILE -c feature -v rel -r char
'''


import argparse
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
from uts import *


def create_arg_parser():
    '''Create argument parser'''
    parser = argparse.ArgumentParser()
    # Parameter that are import to set
    parser.add_argument('-i', "--input_file", default='', type=str, help="DRS input-file")
    parser.add_argument("-s", "--sentence_file", required=True, type=str, help="Sentence file")
    parser.add_argument("-c", "--casing", default='normal', choices=['normal', 'lower', 'feature'],
        help="What do we do with casing? Default 'normal' means do nothing")
    parser.add_argument("-v", "--variables", default='rel', choices=['rel', 'abs', 'none'],
        help="How do we rewrite the variables, relatively (default), absolute or not at all?")
    parser.add_argument("-r", "--representation", default='char', choices=['char', 'word', 'char_word'],
        help="What is the representation of the source/target: characters (default), words or chars+words?")

    # (Boolean) parameters that can influence the process
    parser.add_argument("-so", "--sents_only", action='store_true', help="Only process the sentence file to character-level")
    parser.add_argument("-ne", "--no_error", action='store_true', help="Do not raise error when encountering one in preprocessing, simply ignore that DRS")

    # Parameters that can often be left at default
    parser.add_argument("-cd", "--char_drs_ext", default='.char.drs', type=str, help="Default extension for DRS in character format ")
    parser.add_argument("-cs", "--char_sent_ext", default='.char.sent', type=str, help="Default extension for sentence in character format")
    parser.add_argument("-vd", "--var_drs_ext", default='.var', type=str, help="Default extension for the human-readable variable format")
    args = parser.parse_args()

    if not args.sents_only and not args.input_file:
        raise ValueError("--input_file must be specified if -so is not used")

    return args


def char_level(new_clauses):
    '''Return to string format, char-level for concepts'''
    return_strings = []
    keep_word = ['"now"', '"speaker"', '"hearer"']
    for cur_clause in new_clauses:
        ret_str = ''
        for idx, item in enumerate(cur_clause):
            if between_quotes(item) and item not in keep_word:  #items between quotes are characters, except the ones in keep_word
                item = " ".join(cur_clause[idx])
            elif idx == 1 and not all_upper(item) and not is_role(item): #concepts and roles are kept as is
                item = " ".join(cur_clause[idx])
            ret_str += ' ' + item + ' |||'
        return_strings.append(" ".join(ret_str.rstrip('|||').strip().split()))
    return return_strings


def word_level(new_clauses):
    '''Return to string-format, keep word-level for concepts'''
    return_strings = []
    for cur_clause in new_clauses:
        ret_str = ''
        for item in cur_clause:
            ret_str += ' ' + item + ' |||'
        return_strings.append(" ".join(ret_str.rstrip('|||').strip().split()))
    return return_strings


def new_var_name(item, var_order, cur_var, vars_seen):
    '''Return new variable name, use order of introduction to get it'''
    ref_value = var_order.index(item)
    value = (ref_value - cur_var) + 1
    return '@' + str(value), vars_seen


def get_box_var(var, boxes_seen, new_clauses):
    '''Get the value of the box variable needed'''
    if var not in boxes_seen:
        boxes_seen.append(var)
        return '$NEW', boxes_seen, new_clauses #indicate that we saw a new box
    else:
        # Else check where we are with seeing boxes, and where the box is we refer to
        cur_box = boxes_seen.index(var)
        value = (cur_box - len(boxes_seen)) + 1
        return '$' + str(value), boxes_seen, new_clauses


def rewrite_drss_relative(drs):
    '''Rewrite DRS variables to a more general standard -- relative naming'''
    # Remove comments and split
    drs = [x for x in drs if x.strip() and not x.startswith('%')]
    drs_split = [clause.split()[0:clause.split().index('%')] if '%' in clause.split() else clause.split() for clause in drs]

    # Get order of REFs
    var_order = [x[2] for x in drs_split if x[1] == 'REF']
    new_clauses, vars_seen, boxes_seen = [], [], []
    cur_var = 0

    for cur_clause in drs_split:
        # Clause has 3 items
        if len(cur_clause) == 3:
            # Rewrite box variable
            first_var, boxes_seen, new_clauses = get_box_var(cur_clause[0], boxes_seen, new_clauses)
            # REF is a special case, it introduces a variable
            if cur_clause[1] == 'REF':
                new_clauses.append([first_var, cur_clause[1]])
                cur_var += 1 #saw a new var, so increase cur_var
            elif cur_clause[1] in op_boxes: #handle box variables
                second_var, boxes_seen, new_clauses = get_box_var(cur_clause[2], boxes_seen, new_clauses)
                new_clauses.append([first_var, cur_clause[1], second_var])
            else: #otherwise treat it as a discourse variable
                second_var, vars_seen = new_var_name(cur_clause[2], var_order, cur_var, vars_seen)
                new_clauses.append([first_var, cur_clause[1], second_var])
        # Clause has 4 items
        else:
            first_var, boxes_seen, new_clauses = get_box_var(cur_clause[0], boxes_seen, new_clauses)
            # Second item is an operator
            if all_upper(cur_clause[1]):
                # Handle second variable
                second_var, third_var = cur_clause[2], cur_clause[3] #defaults
                if not between_quotes(cur_clause[2]):
                    if not (cur_clause[1] in op_boxes and cur_clause[1] != 'PRP'):
                        second_var, vars_seen = new_var_name(cur_clause[2], var_order, cur_var, vars_seen)
                # Handle third variable (if there)
                if not between_quotes(cur_clause[3]):
                    if cur_clause[1] == 'PRP':
                        second_var, vars_seen = new_var_name(cur_clause[2], var_order, cur_var, vars_seen)
                        third_var, boxes_seen, new_clauses = get_box_var(cur_clause[3], boxes_seen, new_clauses)
                    elif cur_clause[1] in op_boxes:
                        second_var, boxes_seen, new_clauses = get_box_var(cur_clause[2], boxes_seen, new_clauses)
                        third_var, boxes_seen, new_clauses = get_box_var(cur_clause[3], boxes_seen, new_clauses)
                    else:
                        third_var, vars_seen = new_var_name(cur_clause[3], var_order, cur_var, vars_seen)
                new_clauses.append([first_var, cur_clause[1], second_var, third_var])
            # Second item is a role
            elif is_role(cur_clause[1]):
                second_var, vars_seen = new_var_name(cur_clause[2], var_order, cur_var, vars_seen)
                if not between_quotes(cur_clause[3]):
                    third_var, vars_seen = new_var_name(cur_clause[3], var_order, cur_var, vars_seen)
                else:
                    third_var = cur_clause[3]
                new_clauses.append([first_var, cur_clause[1], second_var, third_var])
            # Otherwise it must be a concept (b1 work "v.01" x2)
            else:
                third_var, vars_seen = new_var_name(cur_clause[3], var_order, cur_var, vars_seen)
                new_clauses.append([first_var, cur_clause[1], cur_clause[2], third_var])
    return new_clauses


def get_from_dict(key, dic, ident):
    '''Check if item is in dictionary, if so use that, else add to dict'''
    if key not in dic:
        item = ident + str(len(dic))
        dic[key] = item
    else:
        item = dic[key]
    return item, dic


def rewrite_drss_absolute(drs):
    '''Rewrite DRS variables to a more general standard -- absolute naming'''
    new_clauses = []

    ## Remove comments and split
    drs = [x for x in drs if x.strip() and not x.startswith('%')]
    drs_split = [clause.split()[0:clause.split().index('%')] if '%' in clause.split() else clause.split() for clause in drs]
    box_dict, var_dict = {}, {} #dicts to keep track of variable names
    box_id, var_id = '$', '@'

    for cur_clause in drs_split:
        # Clause has 3 items
        if len(cur_clause) == 3:
            # Rewrite box variable
            first_var, box_dict = get_from_dict(cur_clause[0], box_dict, box_id)
            if cur_clause[1] in op_boxes: #handle box variables
                second_var, box_dict = get_from_dict(cur_clause[2], box_dict, box_id)
                new_clauses.append([first_var, cur_clause[1], second_var])
            else:
                second_var, var_dict = get_from_dict(cur_clause[2], var_dict, var_id)
                new_clauses.append([first_var, cur_clause[1], second_var])

        # Clause has 4 items
        else:
            first_var, box_dict = get_from_dict(cur_clause[0], box_dict, box_id)
            # Second item is an operator
            if all_upper(cur_clause[1]):
                # Handle second variable
                second_var, third_var = cur_clause[2], cur_clause[3] #defaults
                if not between_quotes(cur_clause[2]):
                    if not (cur_clause[1] in op_boxes and cur_clause[1] != 'PRP'):
                        second_var, var_dict = get_from_dict(cur_clause[2], var_dict, var_id)
                # Handle third variable (if there)
                if not between_quotes(cur_clause[3]):
                    if cur_clause[1] == 'PRP':
                        second_var, var_dict = get_from_dict(cur_clause[2], var_dict, var_id)
                        third_var, box_dict = get_from_dict(cur_clause[3], box_dict, box_id)
                    elif cur_clause[1] in op_boxes:
                        second_var, box_dict = get_from_dict(cur_clause[2], box_dict, box_id)
                        third_var, box_dict = get_from_dict(cur_clause[3], box_dict, box_id)
                    else:
                        third_var, var_dict = get_from_dict(cur_clause[3], var_dict, var_id)
                new_clauses.append([first_var, cur_clause[1], second_var, third_var])
            # Second item is a role
            elif is_role(cur_clause[1]):
                second_var, var_dict = get_from_dict(cur_clause[2], var_dict, var_id)
                if not between_quotes(cur_clause[3]):
                    third_var, var_dict = get_from_dict(cur_clause[3], var_dict, var_id)
                else:
                    third_var = cur_clause[3]
                new_clauses.append([first_var, cur_clause[1], second_var, third_var])
            # Otherwise it must be a concept (b1 work "v.01" x2)
            else:
                third_var, var_dict = get_from_dict(cur_clause[3], var_dict, var_id)
                new_clauses.append([first_var, cur_clause[1], cur_clause[2], third_var])
    return new_clauses


def char_word_level(sents):
    '''Format input in such a way that it contains both character and word-level information
       Input sentences are already in character-level format'''
    new_sents = []
    features = ['***', '^^^']
    for sent in sents:
        new_str = []
        cur_word = ''
        for char in sent.split():
            if char == '|||': #word boundary, so add full word we have now
                new_str.append(cur_word)
                new_str.append(char)
                cur_word = '' #reset current word
            else:
                if char not in features: #features regarding capitalization are not part of the word
                    cur_word += char
                new_str.append(char)

        # Still have to add the last word
        if cur_word: #remove last punctuation if necessary
            if cur_word[-1].isalpha():
                new_str.append(cur_word)
            else:
                new_str = new_str[0:-1] + [cur_word[0:-1]] + ['|||'] + [new_str[-1]]
        new_sents.append(" ".join(new_str))
    return new_sents


def char_tokenization(in_sents):
    '''Do character-level tokenization'''
    # ||| is the character that indicates a space
    sents = [" ".join(" ".join(" ".join(x.split()).replace(' ', '|||')).replace('| | |', '|||').split()) for x in in_sents]
    # We have to change back uppercase features that got split into individual characters in the previous step
    sents = [" ".join(x.replace('^ ^ ^', '^^^').split()) for x in sents]
    return sents


def do_casing(in_sents, casing):
    '''Decide what we do with the casing of the input sentences here
       Options: normal, lower, feature'''
    if casing == 'normal':
        return in_sents
    elif casing == 'lower':
        return [x.lower() for x in in_sents]
    elif casing == 'feature': #add lowercase, but add a feature indicating that it was uppercase before
        feature = '^^^'
        sents = []
        for sent in in_sents:
            new_str = "".join([feature + char.lower() if char.isupper() else char for char in sent])
            sents.append(new_str)
        return sents


def preprocess_sents(sents, args):
    '''Preprocess the sentences, e.g. choose tokenization, choose casing method
       and put in character or word-level format'''
    # Add features for casing (possibly)
    sents = do_casing(sents, args.casing)

    # Then put in char/word level output - for word level we don't have to do anything
    if args.representation == 'char':
        sents = char_tokenization(sents)
    elif args.representation == 'word':
        sents = [" ".join(s.replace(' ', ' ||| ').replace('^^^', ' ^^^ ').strip().split()) for s in sents]
    elif args.representation == 'char_word': #keep both char-level and word-level information
        # First do char and then merge back to words as well
        sents = char_tokenization(sents)
        sents = char_word_level(sents)
    return sents


if __name__ == "__main__":
    args = create_arg_parser()

    # First do the sentences
    sents = [x.strip() for x in open(args.sentence_file, 'r')]
    sents = preprocess_sents(sents, args)
    write_to_file(sents, args.sentence_file + args.char_sent_ext)

    # Check if we do the DRS file as well
    if not args.sents_only:
        # Get list of DRSs and sentences
        drss = get_drss(args.input_file)
        sents = [x.strip() for x in open(args.sentence_file, 'r')]

        # Rewrite DRS variables
        rewritten_drss, var_format = [], []
        errors = 0
        print 'Rewriting variables: {0}'.format(args.variables)

        for idx, drs in enumerate(drss):
            # Rewrite the variables
            try:
                if args.variables == 'rel':
                    rewritten_drs = rewrite_drss_relative(drs)
                elif args.variables == 'abs':
                    rewritten_drs = rewrite_drss_absolute(drs)
                elif args.variables == 'none':
                    drs = [x for x in drs if x.strip() and not x.startswith('%')]
                    rewritten_drs = [clause.split()[0:clause.split().index('%')] if '%' in clause.split() else clause.split() for clause in drs]
                var_format.append([" ".join(x) for x in rewritten_drs])

                # If we use "word", do not do char level
                if args.representation == 'word':
                    char_level_drs = word_level(rewritten_drs)
                else:
                    char_level_drs = char_level(rewritten_drs)

                # Insert special clause separation character
                one_line_drs = " *** ".join(char_level_drs)
                rewritten_drss.append(one_line_drs)
            # The input is expected to be in a certain format
            # However sometimes something can go wrong, we either ignore those
            # instances or throw an error
            except Exception as error:
                if args.no_error:
                    errors += 1
                    print "WARNING: an error occured, ignore DRS {0}".format(idx+1)
                else:
                    raise ValueError(error)

        # Write all output files we want to keep
        print "{0} DRSs not preprocessed because an error occurred".format(errors)
        write_to_file(rewritten_drss, args.input_file + args.char_drs_ext)          #input for machine learning model
        write_list_of_lists(var_format, args.input_file + args.var_drs_ext)    #human readable var format

