#!/usr/bin/env python
# -*- coding: utf8 -*-

'''
Script that preprocess DRS-clause files and puts them in a format for sequence-to-sequence algorithms
Example usage (python3): python preprocess.py -i INPUT_FILE -s SENT_FILE -c feature -v rel -r char
'''

import argparse
import sys
import copy
from uts import write_to_file, write_list_of_lists, get_drss, is_operator, between_quotes, op_boxes, is_role
from concept_to_wordnet import conc_to_wordnet
from clf_referee import check_clf
from clf_referee import get_signature


def create_arg_parser():
    '''Create argument parser'''
    parser = argparse.ArgumentParser()
    # Parameter that are import to set
    parser.add_argument('-i', "--input_file", default='', type=str, help="DRS input-file")
    parser.add_argument("-s", "--sentence_file", default='', type=str, help="Sentence file")
    parser.add_argument("-c", "--casing", default='normal', choices=['normal', 'lower', 'feature'],
                        help="What do we do with casing? Default 'normal' means do nothing")
    parser.add_argument("-v", "--variables", default='rel', choices=['rel', 'abs', 'none'],
                        help="How do we rewrite the variables, relatively (default), absolute or not at all?")
    parser.add_argument("-r", "--representation", default='char', choices=['char', 'word', 'char_word'],
                        help="What is the representation of the source/target: characters (default), words or chars+words?")
    # Whether we want to remove ill-formed DRSs
    # Only use this for training a model, NOT for testing dev/test sets!
    parser.add_argument("-sig", "--sig_file", default='', type=str, help="Signature file for format checking")
    parser.add_argument("-ri", "--remove_ill", action='store_true', help="Remove ill-formed DRSs from the set (need signature as well)")
    # (Boolean) parameters that can influence the process
    parser.add_argument("-so", "--sents_only", action='store_true', help="Only process the sentence file to character-level")
    parser.add_argument("-do", "--drss_only", action='store_true', help="Only process DRS file to char-level")
    parser.add_argument("-ns", "--no_sents", action='store_true', help="Do not preprocess the sentence file, just leave as is")
    parser.add_argument("-ne", "--no_error", action='store_true', help="Do not raise error when encountering one in preprocessing, simply ignore that DRS")
    parser.add_argument("-wn", "--wordnet_exp", action='store_true', help="We are doing a WordNet experiment, convert WN concepts to WN ids")
    parser.add_argument("-wnf", "--wordnet_file", default="", help="WordNet file for doing the conversion")


    # Parameters that can often be left at default
    parser.add_argument("-se", "--sep", default='|||', type=str, help="Space-separator used")
    parser.add_argument("-cd", "--char_drs_ext", default='.char.tgt', type=str, help="Default extension for DRS in character format ")
    parser.add_argument("-cs", "--char_sent_ext", default='.char.sent', type=str, help="Default extension for sentence in character format")
    parser.add_argument("-vd", "--var_drs_ext", default='.var', type=str, help="Default extension for the human-readable variable format")
    parser.add_argument("-va", "--valid_drs_ext", default='.valid', type=str, help="Default extension for all well-formed DRSs (if --remove_ill is used)")
    args = parser.parse_args()

    if not args.sents_only and not args.input_file:
        raise ValueError("--input_file must be specified if -so is not used")
    if not args.input_file and not args.sentence_file:
        raise ValueError("Specify at least 1 out of -i and -s")
    if args.wordnet_exp and not args.wordnet_file:
        raise ValueError("Specify -wnf when using -wn")
    if args.remove_ill and not args.sig_file:
        raise ValueError("Always specify --sig_file when using --remove_ill")
    if args.sig_file and not args.remove_ill:
        print("WARNING: signature file is specified but doesn't do anything without --remove_ill")
    return args


def char_level(new_clauses):
    '''Return to string format, char-level for concepts'''
    return_strings = []
    keep_word = ['"now"', '"speaker"', '"hearer"', '"+"']
    for cur_clause in new_clauses:
        ret_str = ''
        for idx, item in enumerate(cur_clause):
            if between_quotes(item) and cur_clause[1] == 'Name' and idx == 3:
                item = " ".join(item)
            elif between_quotes(item) and item not in keep_word:  #items between quotes are characters, except the ones in keep_word
                item = " ".join(cur_clause[idx])
            elif idx == 1 and not is_operator(item) and not is_role(item): #concepts and roles are kept as is
                item = " ".join(item)
            ret_str += ' ' + item + ' ' + args.sep
        return_strings.append(" ".join(ret_str.rstrip(args.sep).strip().split()))
    return return_strings


def sanitize_variables(drs):
    '''Sanitize DRS variables: make sure that variables are not
       introduced twice (happens for t1). If it happens, remove all
       occurences after the second introduction of t1 to t100 (or more)'''
    count = 100
    cur_refs = []
    rewrite_as = {}
    new_clauses = []
    for clause in drs:
        if clause[1] == 'REF':
            if clause[2] in cur_refs:
                # Already introduced this disc variable by a REF before
                # So rewrite to a variable we have not seen, e.g. b1 REF t1 to b1 REF t100
                # Save this information, so if we encounter t1 in box b1 again, we know to rewrite t1 to t100
                rewrite_as[(clause[0], clause[2])] = 'x' + str(count)
                count += 1 # update count for when disc refs are introduced more than twice
                new_clauses.append([clause[0], clause[1], rewrite_as[(clause[0], clause[2])]])
            else:
                # Save that we saw this REF, but since it's the first time just update
                cur_refs.append(clause[2])
                new_clauses.append(clause)
        else:
            cur_clause = copy.deepcopy(clause)
            # Loop over position 3 and possibly 4 to look for discourse variables that we might want to fix
            for idx, val in enumerate(clause[2:]):
                if (clause[0], val) in rewrite_as:
                    # Found box + variable in list of things we rewrite, do so in cur_clause
                    cur_clause[idx+2] = rewrite_as[(clause[0], val)]
            new_clauses.append(cur_clause)
    return new_clauses


def word_level(new_clauses):
    '''Return to string-format, keep word-level for concepts'''
    return_strings = []
    for cur_clause in new_clauses:
        ret_str = ''
        for item in cur_clause:
            ret_str += ' ' + item + ' ' + args.sep
        return_strings.append(" ".join(ret_str.rstrip(args.sep).strip().split()))
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
    # Else check where we are with seeing boxes, and where the box is we refer to
    cur_box = boxes_seen.index(var)
    value = (cur_box - len(boxes_seen)) + 1
    return '$' + str(value), boxes_seen, new_clauses


def rewrite_drss_relative(drs):
    '''Rewrite DRS variables to a more general standard -- relative naming'''
    # Get order of REFs
    var_order = [x[2] for x in drs if x[1] == 'REF']
    new_clauses, vars_seen, boxes_seen = [], [], []
    cur_var = 0

    for cur_clause in drs:
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
            if is_operator(cur_clause[1]):
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
                second_var, third_var = cur_clause[2], cur_clause[3]
                if not between_quotes(cur_clause[2]):
                    second_var, vars_seen = new_var_name(cur_clause[2], var_order, cur_var, vars_seen)
                if not between_quotes(cur_clause[3]):
                    third_var, vars_seen = new_var_name(cur_clause[3], var_order, cur_var, vars_seen)
                new_clauses.append([first_var, cur_clause[1], second_var, third_var])
            # Otherwise it must be a concept (b1 work "v.01" x2)
            else:
                third_var = cur_clause[3]
                if not between_quotes(cur_clause[3]):
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
    box_dict, var_dict = {}, {} #dicts to keep track of variable names
    box_id, var_id = '$', '@'

    for cur_clause in drs:
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
            if is_operator(cur_clause[1]):
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
            if char == args.sep: #word boundary, so add full word we have now
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
                new_str = new_str[0:-1] + [cur_word[0:-1]] + [args.sep] + [new_str[-1]]
        new_sents.append(" ".join(new_str))
    return new_sents


def char_tokenization(in_sents):
    '''Do character-level tokenization'''
    # + is the character that indicates a space
    sents = [" ".join(" ".join(" ".join(x.split()).replace(' ', args.sep)).replace(" ".join(args.sep), args.sep).split()) for x in in_sents]
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


def drs_string_to_list(drs):
    '''Change a DRS in string format (single list) to a list of lists
       Also remove comments from the DRS'''
    drs = [x for x in drs if x.strip() and not x.startswith('%')]
    drs = [clause.split()[0:clause.split().index('%')] if '%' in clause.split() else clause.split() for clause in drs]
    return drs


def preprocess_sents(sents, args):
    '''Preprocess the sentences, e.g. choose tokenization, choose casing method
       and put in character or word-level format'''
    # Add features for casing (possibly)
    sents = do_casing(sents, args.casing)

    # Then put in char/word level output - for word level we don't have to do anything
    if args.representation == 'char':
        sents = char_tokenization(sents)
    elif args.representation == 'word':
        sents = [" ".join(s.replace(' ', ' {0} '.format(args.sep)).replace('^^^', ' ^^^ ').strip().split()) for s in sents]
    elif args.representation == 'char_word': #keep both char-level and word-level information
        # First do char and then merge back to words as well
        sents = char_tokenization(sents)
        sents = char_word_level(sents)
    return sents


def remove_ill_formed_drss(drss, signature_file):
    '''Remove ill-formed DRSs from a set of DRSs'''
    # Get signature to do the checking
    signature = get_signature(signature_file)

    # Loop over DRSs and only keep valid ones
    new_drss, remove_idxs = [], []
    for idx, drs in enumerate(drss):
        # Remove comments and split
        list_drs = drs_string_to_list(drs)
        try:
            _ = check_clf([tuple(c) for c in list_drs], signature, v=0)
            new_drss.append(drs)
        # DRS invalid, ignore
        except RuntimeError:
            remove_idxs.append(idx)
    return new_drss, remove_idxs


if __name__ == "__main__":
    args = create_arg_parser()

    # First do the sentences
    if not args.drss_only:
        sents = [x.strip() for x in open(args.sentence_file, 'r')]
        if not args.no_sents:
            sents = preprocess_sents(sents, args)


    # Check if we do the DRS file as well
    if not args.sents_only:
        # Get list of DRSs
        drss = get_drss(args.input_file)

        # Check if we ignore ill-formed DRSs perhaps
        # Keep track of the idxs we remove so we can perhaps fix sentences as well
        if args.remove_ill:
            drss, remove_idxs = remove_ill_formed_drss(drss, args.sig_file)
            print("{0} DRSs ignored because they were invalid (referee)".format(len(remove_idxs)))
            # Write all the current valid ones to a file as well
            write_list_of_lists(drss, args.input_file + args.valid_drs_ext)

        # Check if we want to rewrite the concepts to a WordNet representation
        if args.wordnet_exp:
            drss, not_found = conc_to_wordnet(drss, args.wordnet_file)

        # Rewrite DRS variables
        rewritten_drss, var_format = [], []
        errors = 0
        print('Rewriting variables: {0}'.format(args.variables))

        for idx, drs in enumerate(drss):
            # Remove comments and split
            drs = drs_string_to_list(drs)

            # Sanitze DRS variables, sometimes e.g. t1 can be twice introduced by a REF
            drs = sanitize_variables(drs)

            # Rewrite the variables
            try:
                if args.variables == 'rel':
                    rewritten_drs = rewrite_drss_relative(drs)
                elif args.variables == 'abs':
                    rewritten_drs = rewrite_drss_absolute(drs)
                elif args.variables == 'none':
                    rewritten_drs = copy.deepcopy(drs)
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
                    print("WARNING: an error occured, ignore DRS {0}".format(idx+1))
                else:
                    raise ValueError(error)

        # Write all output files we want to keep
        print("{0} DRSs not preprocessed because an error occurred".format(errors))
        write_to_file(rewritten_drss, args.input_file + args.char_drs_ext)     # input for machine learning model
        write_list_of_lists(var_format, args.input_file + args.var_drs_ext)    # human readable var format

    # Print sentences all the way at the end, because we might want to remove certain sents by idx
    # because their DRS was ill-formed (which we don't check until later). Do that check here
    if not args.drss_only:
        if args.remove_ill:
            sents = [s for idx, s in enumerate(sents) if idx not in remove_idxs]
        write_to_file(sents, args.sentence_file + args.char_sent_ext)
