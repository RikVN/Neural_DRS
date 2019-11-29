#!/usr/bin/env python
# -*- coding: utf8 -*-

'''
Script that postprocesses DRS clauses produced by a neural seq2seq parser
Example usage (python3): python postprocess.py -i INPUT_FILE -o OUTPUT_FILE -v rel -s clf_signature.yaml
'''

import argparse
import sys
import copy
import os
import json

from clf_referee import check_clf
from clf_referee import get_signature
from clf_referee import clf_typing
from clf_referee import clf_to_box_dict
from uts import write_list_of_lists, op_boxes, is_operator, is_role, between_quotes, is_concept
#from concept_to_wordnet import wordnet_to_conc, get_wn_dict


def create_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_file", required=True, type=str, help="Input file")
    parser.add_argument("-o", "--output_file", required=True, type=str, help="Output file")
    parser.add_argument("-v", "--var", default='rel', choices=['rel', 'abs', 'none'], help="How do we rewrite the variables, relatively (default), absolute or not necessary?")
    parser.add_argument("-s", "--sig_file", default='', type=str, help="Signature file for format checking")
    parser.add_argument("-n", "--no_referee", action="store_true", help="Don't do referee - just give back output")
    parser.add_argument("-rc", "--remove_concepts", type=int, default=0,
                        help="Remove concepts that occur more often than X times (default 0 means no removal). This helps if you parse longer sentences and the parser gets into a loop. \
                              Note that this setting was not used for the TACL paper experiments.")
    parser.add_argument("-rr", "--remove_roles_op", type=int, default=0,
                        help="Remove roles and operators that occur more often than X times (default 0 means no removal). This helps if you parse longer sentences and the parser gets into a loop. \
                              Note that this setting was not used for the TACL paper experiments.")
    parser.add_argument("-rcl", "--remove_clauses", type=int, default=0,
                        help="Simply remove all clauses after this number (default 0 means no removal). This helps if you parse longer sentences and the parser gets into a loop. \
                              Note that this setting was not used for the TACL paper experiments.")
    parser.add_argument("-se", "--sep", default='|||', type=str, help="Space-separator used")
    parser.add_argument("-f", "--fix", action='store_true', help="Try to fix DRSs for which referee returned 'no main box found' or 'subordinate relation has a loop' ")
    parser.add_argument("-j", "--json", action='store_true', help="Input file is in JSON format (AllenNLP)")
    parser.add_argument("-voc", "--vocab", type=str, help="Vocab of AllenNLP experiment, only necessary when using --json as well")
    parser.add_argument("-m", "--min_tokens", type=int, default=20, help="Minimum amount of tokens (only for AllenNLP exp with --json). If not enough tokens we take different beam answer")
    parser.add_argument("-b", "--baseline", action='store_true', help="Add baseline DRS instead of dummy DRS when DRS is invalid")
    parser.add_argument("-fs", "--fix_senses", default='', type=str, help="If added, it's a file with a list of training set words + senses in this format: count word sense. We use it to fix word senses")
    parser.add_argument("-wn", "--wordnet_exp", action='store_true', help="We were doing a WordNet experiment, restore WN interlingua by actual concepts before doing other stuff")
    parser.add_argument("-wnf", "--wordnet_file", default="", help="WordNet file for doing the conversion")
    args = parser.parse_args()
    if (args.remove_concepts == 0 or args.remove_roles_op == 0) and (args.remove_concepts > 0 or args.remove_roles_op > 0):
        raise ValueError("Either have --remove_concepts AND --remove_roles > 0, or have both at 0")
    if args.input_file == args.output_file:
        raise ValueError("Input and output file are the same")
    if args.wordnet_exp and not args.wordnet_file:
        raise ValueError("Specify -wnf when using -wn")
    if args.json and not args.vocab:
        raise ValueError("Always specify --vocab when doing an AllenNLP experiment using --json")
    return args


def dummy_drs(list_output=True):
    '''Return dummy or baseline DRS in clause format'''
    if not args.baseline:
        if list_output:
            return [['b1', 'REF', 'x1'], ['b1', 'alwayswrongconcept', '"n.01"', 'x1']]
        return ['b1 REF x1', 'b1 alwayswrongconcept "n.01" x1']
    else:
        baseline = ['b1 REF x1',
                    'b1 Name x1 "tom"',
                    'b1 male "n.02" x1',
                    'b2 REF e1',
                    'b2 REF t1',
                    'b2 Agent e1 x1',
                    'b2 TPR t1 "now"',
                    'b2 Time e1 t1',
                    'b2 time "n.08" t1',
                    'b2 vote "v.01" e1',
                    'b2 Theme e1 x1']
        if list_output:
            return [x.split() for x in baseline]
        return baseline


def replace_double_space(line):
    '''If we accidentally output two spaces for a role, output the previous variable two times
       This way the matching always goes wrong (so the mistake is punished), but we do have a valid DRS still'''
    new_list = []
    if line.strip(): #catch empty line
        spl_line = line.split()
        # If first item is a space we just remove it
        if spl_line[0] == args.sep:
            spl_line = spl_line[1:]

        for idx, item in enumerate(spl_line):
            if item == args.sep and spl_line[idx-1] == args.sep:
                new_list.append(new_list[-2])
            else:
                new_list.append(item)
    return " ".join(new_list)


def restore_variables(drs, var, idx, pp_dict):
    '''Restore the variables of the output DRSs '''
    try:
        # Important difference between relative and absolute descriptions of variables here
        if var == 'rel':
            var_drs, pp_dict = restore_variables_relative(drs, idx, pp_dict)
        elif var == 'abs':
            var_drs, pp_dict = restore_variables_absolute(drs, idx, pp_dict)
        elif var == 'none':
            var_drs = []
            for clause in drs:
                cur_clause = clause.split()[0:clause.split().index('%')] if '%' in clause.split() else clause.split()
                if len(cur_clause) in [3, 4]:
                    var_drs.append(cur_clause)
                else:
                    pp_dict["variables"] += 1
                    print('DRS {0}: Ignoring clause {1} because of wrong arity'.format(idx, clause))
    except:
        var_drs = [" ".join(x) for x in dummy_drs()]
        pp_dict["dummies-pp"] += 1
    return var_drs, pp_dict


def restore_clauses(line, remove_clauses, idx, pp_dict):
    '''Restore clauses from one-line format with placeholder characters to list of lists with clauses'''
    # Sometimes we output a space where we should have a put a concept or variable
    # In case of a concept we just put a default "male", in case of a variable we replace
    # it by the same variable already used in the DRS (for some reason it's always the last one that is wrong)
    line = line.replace('{0} {0} {0}'.format(args.sep), '{0} male {0}'.format(args.sep)).replace('▁', '')
    line = replace_double_space(line)
    # For a + separator we have to be careful not to remove a normal +
    if args.sep == '+':
        # Do not remove the + in "+"
        line = line.replace('"+"', 'TMPSAVE').replace(' ', '').replace('+', ' ').replace('TMPSAVE', '"+"')
    else:
        line = line.replace(' ', '').replace(args.sep, ' ')
    # Change line to a list of clauses
    clause_list = line.split('***')
    # Remove clauses after a certain amount (if specified)
    if remove_clauses > 0 and len(clause_list) > remove_clauses:
        print('DRS {0}: Removing clauses after clause {1} for total length {2}'.format(idx, remove_clauses, len(line)))
        pp_dict["restore"] += 1
        clause_list = clause_list[0:remove_clauses]
    return clause_list, pp_dict


def remove_clauses_by_freq(drs, rm_concepts, rm_roles_op, idx, pp_dict):
    '''For each DRS, remove certain clauses if they occur too often'''
    if rm_concepts > 0:
        drs, pp_dict = remove_concepts(drs, rm_concepts, idx, pp_dict)
    if rm_roles_op > 0:
        drs, pp_dict = remove_roles_operators(drs, rm_roles_op, idx, pp_dict)
    return drs, pp_dict


def get_disc_refs(drs):
    '''Get all discourse referents that occur in non-REF clauses'''
    disc_refs = []
    for cur_clause in drs:
        if cur_clause[1] != 'REF':
            # If the identifier is not in op_boxes we found a discourse referent
            if len(cur_clause) == 3:
                if cur_clause[1] not in op_boxes and not between_quotes(cur_clause[2]):
                    if cur_clause[2] not in disc_refs:
                        disc_refs.append([cur_clause[0], cur_clause[2], cur_clause])
            else: # Clause has 4 items
                #Everything that is not between quotes for item 3/4 is a disc ref, except when it is box variable due to the operator
                if (cur_clause[1] not in op_boxes or cur_clause[1] == 'PRP') and not between_quotes(cur_clause[2]):
                    if cur_clause[2] not in disc_refs:
                        disc_refs.append([cur_clause[0], cur_clause[2], cur_clause])
                if cur_clause[1] not in op_boxes and cur_clause[1] != 'PRP' and not between_quotes(cur_clause[3]):
                    if cur_clause[3] not in disc_refs:
                        disc_refs.append([cur_clause[0], cur_clause[3], cur_clause])
    return disc_refs


def check_ref_clauses(drs, drs_idx, pp_dict, do_print=True):
    '''Check if each discourse referent that is used has a REF clause'''
    clause_refs = [[x[2], x] for x in drs if x[1] == 'REF']    # get discourse referents with initial clause
    refs = [x[2] for x in drs if x[1] == 'REF']                # all discourse referents introduced by REF

    # Save discourse referents found in other non-REF clauses
    disc_refs = get_disc_refs(drs)

    # Add missing REF clauses
    for d in disc_refs:
        if d[1] not in refs:
            # Simply add REF clause that is missing
            add_clause = [d[0], "REF", d[1]]
            if do_print:
                print('DRS {0}: REF missing for {1} -- Clause: {2} -- Add clause: {3}'.format(drs_idx, d[1], " ".join(d[2]), add_clause))
                pp_dict["easy"] += 1
            drs.append(add_clause)

    # Remove spurious REF clauses
    for r in clause_refs:
        if r[0] not in [x[1] for x in disc_refs]:
            if do_print:
                print('DRS {0}: {1} instantiated but never referenced -- remove REF'.format(drs_idx, r[0]))
                pp_dict["easy"] += 1
            drs = [d for d in drs if d != r[1]]
    # Check if we didn't remove all clauses (can happen with some strange settings, i.e. sample data)
    if not drs:
        return dummy_drs(list_output=True), pp_dict
    return drs, pp_dict


def check_doubles(drs, drs_idx, pp_dict):
    '''Check if there are double clauses, if so, remove them, but keep order'''
    new_drs = []
    for clause in drs:
        if clause in new_drs:
            # Simply remove double clause, so do nothing except printing
            print('DRS {0}: double clause, remove: {1}'.format(drs_idx, clause))
            pp_dict["easy"] += 1
        else:
            new_drs.append(clause)
    return new_drs, pp_dict


def remove_concepts(drs, rm_concepts, drs_idx, pp_dict):
    '''Remove all concepts that occur more often than rm_concepts times
       Do the same for names -- they might also loop and occur way too often
       This setting was not used in the TACL paper, but might help for
       parsing longer sentences'''
    new_drs, concs, names = [], [], []
    for clause_string in drs:
        clause = clause_string.split()
        if len(clause) > 1 and len(clause[1]) == len([a for a in clause[1] if a.islower()]):
            if concs.count(clause[1]) < rm_concepts:
                new_drs.append(" ".join(clause))
            else:
                print('DRS {0}: removing {1} because concept occurs > {2}'.format(drs_idx, clause_string, rm_concepts))
                pp_dict["frequency"] += 1
            concs.append(clause[1])
        elif len(clause) > 1 and clause[1] == 'Name' and len(clause) == 4:
            if names.count(clause[3]) < rm_concepts:
                new_drs.append(" ".join(clause))
            else:
                print('DRS {0}: removing {1} because name occurs > {2}'.format(drs_idx, clause_string, rm_concepts))
                pp_dict["frequency"] += 1
            names.append(clause[3])
        else:
            new_drs.append(" ".join(clause))
    return new_drs, pp_dict


def remove_roles_operators(drs, rm_roles_op, drs_idx, pp_dict):
    '''Remove all roles AND operators that occur more often than rm_roles_op times
       This setting was not used in the TACL paper, but might help for
       parsing longer sentences'''
    new_drs, roles = [], []
    for clause_string in drs:
        clause = clause_string.split()
        if len(clause) > 1 and clause[1] != 'REF' and clause[1][0].isupper():
            if roles.count(clause[1]) < rm_roles_op:
                new_drs.append(" ".join(clause))
            else:
                print('DRS {0}: removing {1} because role occurs > {2}'.format(drs_idx, clause_string, rm_roles_op))
                pp_dict["frequency"] += 1
            roles.append(clause[1])
        else:
            new_drs.append(" ".join(clause))
    return new_drs, pp_dict


def fix_word_senses(drs, senses, idx, pp_dict):
    '''Try to automatically fix produced word senses'''
    # Loop over clauses in DRS
    for clause_idx, clause in enumerate(drs):
        if is_concept(clause):
            box, concept, sense, var = clause.split()[0:4]
            # First check if full sense occurs, if so, just keep it
            found = False
            for sns in senses:
                if [concept, sense] == sns[1:3]:
                    found = True
            # If not, check if the word occurs with a different sense
            # If true, use that sense instead - so change clause
            if not found:
                for sns in senses:
                    if concept == sns[1] and not found:
                        drs[clause_idx] = " ".join([box, concept, sns[2], var])
                        found = True
                        pp_dict["sense"] += 1
                        print("DRS {0}: changed {1} {2} to {1} {3}".format(idx, concept, sense, sns[2]))
    return drs, pp_dict


def easy_fixes(drs, idx, pp_dict):
    '''Perform some easy output-fixing for trivial errors the model makes'''
    try:
        # Check if there are double clauses (not allowed, so remove them)
        drs, pp_dict = check_doubles(drs, idx, pp_dict)
        # Check if each discourse referent that is used also has a REF
        # So removing spurious REFs, or adding them if necessary
        drs, pp_dict = check_ref_clauses(drs, idx, pp_dict)
    except:
        print('DRS {0}: error when applying "easy" fixes, add dummy DRS'.format(idx))
        drs = dummy_drs(list_output=False)
        pp_dict["dummies-pp"] += 1

    return drs, pp_dict


def box_variable(key, dic):
    '''Check if item is in dictionary, if so use that, else add to dict'''
    if key not in dic:
        item = 'b' + str(len(dic))
        dic[key] = item
    else:
        item = dic[key]
    return item, dic


def new_var_name(item, var_list, cur_var, clause_string, ident, drs_idx, pp_dict):
    '''Get new variable name for references such as @-1 and @1'''
    if item == ident + 'NEW':
        # Deal with newly introduced variables that say new
        return_var = var_list[cur_var]
        cur_var += 1
        return return_var, pp_dict, cur_var
    try:
        ref_num = int(item[1:]) # strip @ from @-1 and @2 etc
    except:
        pp_dict["variables"] += 1
        print('DRS {0}: could not find variable number in {1}, use default 0'.format(drs_idx, item))
        ref_num = 0 #add default 0 if there is no variable in this output

    num = cur_var + ref_num - 1
    if num < 0:
        pp_dict["variables"] += 1
        num = 0 #negative numbers are impossible, closest is then 0, so use that
        print('DRS {0}: impossible negative reference for {1}, use default 0'.format(drs_idx, clause_string))

    # Get variable we are currently referring to
    try:
        second_var = var_list[num]
    except: # Num larger than length of list, take last item
        pp_dict["variables"] += 1
        second_var = var_list[-1]
        print('DRS {0}: impossible reference (longer than list-length) for {1}, use default last item'.format(drs_idx, clause_string))
    return second_var, pp_dict, cur_var


def get_var_order(drs):
    '''Get order of discourse referents based on their introduction'''
    var_order = []
    for clause in drs:
        clause_split = clause.split()
        for item in clause_split:
            if item == '@NEW':
                var_order.append('x' + str(len(var_order) + 1))
    return var_order


def get_box_order(drs):
    '''Number and order of boxes for relative rewriting'''
    box_order = []
    for clause in drs:
        clause_split = clause.split()
        for item in clause_split:
            if item == '$NEW':
                box_order.append('b' + str(len(box_order) + 1))
    return box_order


def restore_variables_relative(drs, drs_idx, pp_dict):
    '''Restore the dummy variable names we used to actual variables -- relatively'''
    # Get order of variable
    var_list = ['x' + str(idx+1) for idx in range(len([1 for idx, x in enumerate(drs) if len(x.split()) > 1 and x.split()[1] == 'REF']))]
    # Get order of boxes
    box_list = get_box_order(drs)

    # Initial settings
    new_clauses = []
    cur_var, cur_box = 0, 0#start value
    box_ident, var_ident = '$', '@'

    for clause_string in drs:
        try:
            cur_clause = clause_string.split()
            # Clause has 2 or 3 items
            if len(cur_clause) in [2, 3]:
                # Restore box variable
                first_var, pp_dict, cur_box = new_var_name(cur_clause[0], box_list, cur_box, clause_string, box_ident, drs_idx, pp_dict)
                if cur_clause[1] == 'REF':
                    # Add REF with x-variable for the REF-case
                    cur_var += 1
                    new_clauses.append([first_var, 'REF', 'x' + str(cur_var)])
                elif cur_clause[1] in op_boxes: #handle box variables
                    second_var, pp_dict, cur_box = new_var_name(cur_clause[2], box_list, cur_box, clause_string, box_ident, drs_idx, pp_dict)
                    new_clauses.append([first_var, cur_clause[1], second_var])
                else:
                    print('DRS {0}: warning, clause {1} gets ignored'.format(drs_idx, clause_string)) #clause is invalid by definition, ignore
                    pp_dict["variables"] += 1
            # Clause has 4 items
            elif len(cur_clause) == 4:
                first_var, pp_dict, cur_box = new_var_name(cur_clause[0], box_list, cur_box, clause_string, box_ident, drs_idx, pp_dict)
                # Second item is an operator
                if is_operator(cur_clause[1]):
                    # Handle second variable
                    second_var, third_var = cur_clause[2], cur_clause[3] #defaults
                    if not between_quotes(cur_clause[2]):
                        if not (cur_clause[1] in op_boxes and cur_clause[1] != 'PRP'):
                            second_var, pp_dict, cur_var = new_var_name(cur_clause[2], var_list, cur_var, clause_string, var_ident, drs_idx, pp_dict)
                    # Handle third variable (if there)
                    if not between_quotes(cur_clause[3]):
                        if cur_clause[1] == 'PRP':
                            second_var, pp_dict, cur_var = new_var_name(cur_clause[2], var_list, cur_var, clause_string, var_ident, drs_idx, pp_dict)
                            third_var, pp_dict, cur_box = new_var_name(cur_clause[3], box_list, cur_box, clause_string, box_ident, drs_idx, pp_dict)
                        elif cur_clause[1] in op_boxes: #get box variable
                            second_var, pp_dict, cur_box = new_var_name(cur_clause[2], box_list, cur_box, clause_string, box_ident, drs_idx, pp_dict)
                            third_var, pp_dict, cur_box = new_var_name(cur_clause[3], box_list, cur_box, clause_string, box_ident, drs_idx, pp_dict)
                        else:
                            third_var, pp_dict, cur_var = new_var_name(cur_clause[3], var_list, cur_var, clause_string, var_ident, drs_idx, pp_dict)
                    new_clauses.append([first_var, cur_clause[1], second_var, third_var])
                # Second item is a role
                elif is_role(cur_clause[1]):
                    second_var, third_var = cur_clause[2], cur_clause[3]
                    # Items not between quotes are variables that need to be rewritten
                    if not between_quotes(cur_clause[2]):
                        second_var, pp_dict, cur_var = new_var_name(cur_clause[2], var_list, cur_var, clause_string, var_ident, drs_idx, pp_dict)
                    if not between_quotes(cur_clause[3]):
                        third_var, pp_dict, cur_var = new_var_name(cur_clause[3], var_list, cur_var, clause_string, var_ident, drs_idx, pp_dict)
                    new_clauses.append([first_var, cur_clause[1], second_var, third_var])
                # Otherwise it must be a concept (b1 work "v.01" x2)
                else:
                    cr_concept = cur_clause[1]
                    third_var, pp_dict, cur_var = new_var_name(cur_clause[3], var_list, cur_var, clause_string, var_ident, drs_idx, pp_dict)
                    ## Put default sense if model did not produce that
                    if not between_quotes(cur_clause[2]) and '"' not in cur_clause[2] and cur_clause[2].islower():
                        print('DRS {0}: no sense was added for concept {1}, add default sense'.format(drs_idx, cur_clause[2]))
                        new_clauses.append([first_var, cr_concept, '"n.01"', third_var])
                        pp_dict["variables"] += 1
                    else:
                        new_clauses.append([first_var, cr_concept, cur_clause[2], third_var])
            else: #clause has wrong length, ignore
                print('DRS {0}: warning, clause {1} gets ignored'.format(drs_idx, clause_string))
                pp_dict["variables"] += 1
        except:
            pp_dict["variables"] += 1
            print('DRS {0}: Error when processing {1} -- ignore clause'.format(drs_idx, clause_string))
    return new_clauses, pp_dict


def get_variable(key, dct, ident):
    '''Check if item is in dictionary, if so use that, else add to dict'''
    if key not in dct:
        item = ident + str(len(dct))
        dct[key] = item
    else:
        item = dct[key]
    return item, dct


def restore_variables_absolute(drs, drs_idx, pp_dict):
    '''Restore the dummy variable names we used to actual variables -- absolute'''
    new_clauses = []
    var_dict, box_dict = {}, {}
    box_id, var_id = 'b', 'x'

    for clause_string in drs:
        try:
            cur_clause = clause_string.split()
            # Clause has 2 or 3 items
            if len(cur_clause) in [2, 3]:
                # Restore box variable
                first_var, box_dict = get_variable(cur_clause[0], box_dict, box_id)
                if cur_clause[1] in op_boxes: #handle box variables
                    second_var, box_dict = get_variable(cur_clause[2], box_dict, box_id)
                else:
                    second_var, var_dict = get_variable(cur_clause[2], var_dict, var_id)
                new_clauses.append([first_var, cur_clause[1], second_var])
            # Clause has 4 items
            else:
                first_var, box_dict = get_variable(cur_clause[0], box_dict, box_id)
                # Second item is an operator
                if is_operator(cur_clause[1]):
                    # Handle second variable
                    second_var, third_var = cur_clause[2], cur_clause[3] #defaults
                    if not between_quotes(cur_clause[2]):
                        if not (cur_clause[1] in op_boxes and cur_clause[1] != 'PRP'):
                            second_var, var_dict = get_variable(cur_clause[2], var_dict, var_id)
                    # Handle third variable (if there)
                    if not between_quotes(cur_clause[3]):
                        if cur_clause[1] == 'PRP':
                            second_var, var_dict = get_variable(cur_clause[2], var_dict, var_id)
                            third_var, box_dict = get_variable(cur_clause[3], box_dict, box_id)
                        elif cur_clause[1] in op_boxes:
                            second_var, box_dict = get_variable(cur_clause[2], box_dict, box_id)
                            third_var, box_dict = get_variable(cur_clause[3], box_dict, box_id)
                        else:
                            third_var, var_dict = get_variable(cur_clause[3], var_dict, var_id)
                    new_clauses.append([first_var, cur_clause[1], second_var, third_var])
                # Second item is a role
                elif is_role(cur_clause[1]):
                    second_var, var_dict = get_variable(cur_clause[2], var_dict, var_id)
                    if not between_quotes(cur_clause[3]):
                        third_var, var_dict = get_variable(cur_clause[3], var_dict, var_id)
                    else:
                        third_var = cur_clause[3]
                    new_clauses.append([first_var, cur_clause[1], second_var, third_var])
                # Otherwise it must be a concept (b1 work "v.01" x2)
                else:
                    third_var, var_dict = get_variable(cur_clause[3], var_dict, var_id)
                    # Put default sense if model did not produce that
                    if not between_quotes(cur_clause[2]) and '"' not in cur_clause[2] and cur_clause[2].islower():
                        print('DRS {0}: no sense was added for concept {1}, add default sense'.format(drs_idx, clause_string))
                        pp_dict["restore"] += 1
                        new_clauses.append([first_var, cur_clause[1], '"n.01"', third_var])
                    else:
                        new_clauses.append([first_var, cur_clause[1], cur_clause[2], third_var])
        except:
            pp_dict["restore"] += 1
            print('DRS {0}: Error when processing {1} -- ignore clause'.format(drs_idx, clause_string))
    return new_clauses, pp_dict


def detect_independent_boxes(box_dict):
    '''Given boxes and a subordinate relationfind independent boxes'''
    # get a set of boxes that are not sitting inside other boxes
    # e.g., presuppositions will be such boxes
    independent_boxes = []
    for b0 in box_dict:
        # there is no b1 that contains b0 in relations or conditions
        if not next((b1 for b1 in box_dict if b0 in box_dict[b1].subs or b0 in box_dict[b1].rel_boxes), False):
            if b0 not in independent_boxes:
                independent_boxes.append(b0)
    # We only get there is there's the "No main box found" error, so we're done now
    return independent_boxes


def possible_changes(idx, clause, unique1, unique2, proposed_changes):
    '''Get possible variable-changes for this clause here'''
    for value in [2, 3]: #check both second and third item
        new_clause = [clause[0], clause[1], clause[2], clause[3]]
        item = clause[value]
        # Loop over the variables to see if we can make a switch
        for var1 in unique1:
            if var1 == item: #match found, try to insert var from unique2
                for var2 in unique2:
                    if var2 not in clause: #var should not already be present
                        new_clause[value] = var2
                        # Save the fact that we change the clause at index idx to the new clause
                        # Later we go over these changes to see if the DRS is valid now
                        if (idx, new_clause) not in proposed_changes:
                            proposed_changes.append((idx, new_clause))
    return proposed_changes


def merge_boxes(clf, boxes):
    '''Merge all boxes in list 'boxes' together in a single box'''
    if len(boxes) >= 2:
        main_box = boxes[0]
        new_clf = []
        for clause in clf:
            new_item = []
            for item in clause:
                added = False
                for b in boxes[1:]:
                    if b == item: #box matches, so add main_box instead of this box
                        new_item.append(main_box)
                        added = True
                if not added:
                    new_item.append(item)
            new_clf.append(tuple(new_item))
        return new_clf
    else:
        return clf


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


def fix_no_main_box(clf, signature, drs_idx, pp_dict):
    '''Automatically try to fix the fact that there's no main box in the DRS
       Usually means there are multiple independent boxes, so, try to change
       one of the discourse variables to a variable of the other box.
       clf is a list of tuples here'''
    # First we need to know what the indepedent boxes are for this DRSs
    # Functions are imported from clf_referee
    # get argument typing and for each clause an operator type
    (op_types, arg_typing) = clf_typing(clf, signature, v=0)
    box_dict = clf_to_box_dict(clf, op_types, arg_typing, v=0)
    # This is a new function that returns independent boxes
    ind_boxes = detect_independent_boxes(box_dict)
    # Get all discourse referents for this clf
    disc_refs = [(x[0], x[1]) for x in get_disc_refs([" ".join(c) for c in clf])]
    proposed_changes = []

    # Loop over them two at the time, but if we fix the DRS already, we're done
    for idx in range(0, len(ind_boxes) -1):
        box1, box2 = ind_boxes[idx+1], ind_boxes[idx]
        # Get specific discourse referents for these boxes
        discs1 = [x[1] for x in disc_refs if x[0] == box1]
        discs2 = [x[1] for x in disc_refs if x[0] == box2]
        # Only keep disc referents that are not already present in the other box
        unique1 = list(set(discs1) - set(discs2))
        unique2 = list(set(discs2) - set(discs1))
        # Loop over the clauses and elements
        proposed_changes = []
        for idx, clause in enumerate(clf):
            if len(clause) == 4: #only these have discourse referents we're interested in
                # Get the changes for both orders of the variables
                proposed_changes = possible_changes(idx, clause, unique1, unique2, proposed_changes)
                proposed_changes = possible_changes(idx, clause, unique2, unique1, proposed_changes)
    # Loop over the proposed changes
    # If we get a valid DRS, break, and return that DRS
    for p in proposed_changes:
        new_drs = list(copy.deepcopy(clf))
        new_drs[p[0]] = tuple(p[1]) #change the clause to the proposed one
        # Check here if we found a valid one
        try:
            _ = check_clf(new_drs, signature, v=0)
            print('DRS {0}: Fixed "No main box found" error by changing clause {1} to {2}'.format(drs_idx, p[0], " ".join(p[1])))
            pp_dict["no main box"] += 1
            return new_drs, pp_dict, False
        except RuntimeError:
            # Still error, pass
            pass

    # We are here because we still did not find anything
    # Last resort: try to merge independent boxes together
    # in a single box. Start with small combinations, but
    # ultimately also try to merge them all together
    try:
        box_list = powerset(ind_boxes) #get all combinations of boxes, ordered by size
    except MemoryError: # function can go out of memory, just return a dummy then
        box_list = []
        print("DRS {0}: WARNING - powerset out of memory, return dummy".format(drs_idx))

    # Loop over the boxes and see if merging gives us a valid DRS
    for boxes in box_list:
        new_clf = merge_boxes(clf, boxes)
        # Check if it is valid now
        try:
            _ = check_clf(new_clf, signature, v=0)
            print('DRS {0}: Fixed "No main box found" error by merging these boxes: {1}'.format(drs_idx, " ".join(boxes)))
            pp_dict["no main box"] += 1
            return new_clf, pp_dict, False
        except RuntimeError:
            # Still invalid, try next one
            pass
    # We found nothing, return dummy DRS
    return dummy_drs(), pp_dict, True


def remove_by_box(clf, box):
    '''Remove all clauses that contain a certain box
       Might help solving subordinate relation loop problems'''
    return [x for x in clf if x[0] != box]


def get_boxes(clf):
    '''Return all boxes in a DRS'''
    boxes = []
    for c in clf:
        if c[0] not in boxes:
            boxes.append(c[0])
    return boxes


def solve_loops(clf, box, signature, drs_idx, pp_dict):
    '''Recursive function: simply remove the box from a DRS that returned
       the subordinate relation has a loop error.
       If the new DRS gets a loop error message,
       then simply remove the new box as well (etc)'''
    # If already empty, return False
    if not clf:
        return False, True, pp_dict

    # First try to merge the offending box with any other box, and see if the DRS is valid now
    boxes = get_boxes(clf)
    for b in boxes:
        if box != b:
            new_clf = merge_boxes(clf, [b, box])
            try:
                _ = check_clf(new_clf, signature, v=0)
                print('DRS {0}: Fixed "subordinate relation has a loop" error by merging these boxes: {1} {2}'.format(drs_idx, b, box))
                # No error means the DRS is now valid, so return
                return new_clf, False, pp_dict
            except RuntimeError as err:
                pass
    # If this is not the case, we remove the offending box
    new_clf = remove_by_box(clf, box)

    # Maybe we need to insert or remove REFs again
    new_clf_tmp, _ = check_ref_clauses(new_clf, drs_idx, {}, do_print=False)
    new_clf = [tuple(x) for x in new_clf_tmp]

    # Check if the new DRS is valid
    try:
        _ = check_clf(new_clf, signature, v=0)
        # No error means the DRS is now valid, so return
        return new_clf, False, pp_dict
    except RuntimeError as err:
        err_message = str(err)
        # Check the error message, if again a loop is the problem, call this function again
        if 'Subordinate relation has a loop' in err_message:
            box_num = err_message.split('||')[1].split('>')[0].strip()
            new_clf, is_dummy, pp_dict = solve_loops(new_clf, box_num, signature, drs_idx, pp_dict)
        # No main box found, we might have a fix for that as well
        elif 'No main box found' in err_message:
            new_clf, pp_dict, is_dummy = fix_no_main_box(new_clf, signature, drs_idx, pp_dict)
            return new_clf, is_dummy, pp_dict
        # Different error, so approach didn't work, quit
        else:
            return False, True, pp_dict
    return new_clf, is_dummy, pp_dict


def extensive_format_check(drs, signature, try_fix, idx, pp_dict):
    '''Do a more extensive semantic format check (referee)
       Also try to fix the DRSs if specified'''
    try:
        _ = check_clf([tuple(c) for c in drs], signature, v=0)
        drs_final = drs
    # DRS invalid, replace by dummy or try to fix
    except RuntimeError as err:
        err_message = str(err)
        # Try to fix no main box found errors
        if try_fix and 'No main box found' in err_message:
            drs_final, pp_dict, is_dummy = fix_no_main_box([tuple(c) for c in drs], signature, idx, pp_dict)
            if is_dummy:
                pp_dict["dummies-ref"] += 1 #still update error counter if we got a dummy back
                print('DRS {0}: invalid DRS: {1}'.format(idx, err_message))

        # Try to fix subordinate loops by just merging/removing the offending box
        elif try_fix and 'Subordinate relation has a loop' in err_message:
            box_num = err_message.split('||')[1].split('>')[0].strip()
            new_drs, is_dummy, pp_dict = solve_loops([tuple(c) for c in drs], box_num, signature, idx, pp_dict)
            # Returns False for new_clf if it didn't work, then add dummy (with the initial message)
            if new_drs and not is_dummy:
                drs_final = [c for c in new_drs]
                pp_dict["sub loop"] += 1
                print('DRS {0}: Fixed subordinate loop problem by removing/merging box {1}'.format(idx, box_num))
            else:
                drs_final = dummy_drs(list_output=True)
                pp_dict["dummies-ref"] += 1
                print('DRS {0}: invalid DRS: {1}'.format(idx, err_message))
        else:
            drs_final = dummy_drs(list_output=True)
            pp_dict["dummies-ref"] += 1
            print('DRS {0}: invalid DRS: {1}'.format(idx, err_message))
    return drs_final, pp_dict


def json_by_line(input_file):
    '''Read input file which is a file of json objects'''
    data = []
    with open(input_file, 'r') as f:
        for line in f:
            data.append(json.loads(line))
    return data


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


def read_json_predictions(input_file, vocab, min_tokens):
    '''Read the json predictions of AllenNLP
       Bit tricky: if predictions for the winning beam are very short
       we take a later prediction and ignore the "winning" beam
       Label smoothing can have this side effect that cuts the sequences
       short otherwise. We need the vocab for that. Raise error if we did
       not specify a vocab to help us remember this issue'''
    vocab = [x.strip() for x in open(vocab, 'r')]
    dict_lines = json_by_line(input_file)
    lines = []
    for i, dic in enumerate(dict_lines):
        tokens = dic["predicted_tokens"]
        if len(tokens) >= min_tokens:
            lines.append(" ".join(tokens))
        # Not enough tokens in output, go down beam search
        else:
            predictions = dic["predictions"][1:] #skip first
            found = 0
            for idx, pred in enumerate(predictions):
                cur_tok = voc_to_tok(pred, vocab)
                if len(cur_tok) >= min_tokens:
                    lines.append(" ".join(cur_tok))
                    found = idx+2
                    break
            # Print output for logging
            if found == 0:
                print("DRS {0}: first beam answer too short but still used".format(i))
                lines.append(" ".join(tokens))
            else:
                print("DRS {0}: first beam answer too short, use beam {1} instead".format(i, found))
    return lines


if __name__ == "__main__":
    args = create_arg_parser()
    print('Start postprocessing...')
    drss = []
    possible_repairs = ["restore", "wordnet", "frequency", "variables", "easy", "sense", "no main box", "sub loop", "dummies-pp", "dummies-ref"]
    pp_dict = dict.fromkeys(possible_repairs, 0)

    # Load sense file in advance so we don't have to do this every time
    senses = [x.split() for x in open(args.fix_senses, 'r')] if args.fix_senses and os.path.isfile(args.fix_senses) else None
    signature = get_signature(args.sig_file) if args.sig_file and os.path.isfile(args.sig_file) else None

    # Check if we have to modify the JSON output first
    if args.json:
        lines = read_json_predictions(args.input_file, args.vocab, args.min_tokens)
    else:
        lines = [x.strip() for x in open(args.input_file, 'r')]

    # Each line is a DRS, loop over them here one-by-one
    for idx, line in enumerate(lines):
        # Restore clause format, we now have a list of clauses (list of strings)
        drs, pp_dict = restore_clauses(line, args.remove_clauses, idx, pp_dict)

        # Wordnet stuff not added for Github version, only local (for now)
        ## Check if we did a WordNet experiment, if yes, restore clauses
        #if args.wordnet_exp:
            #wn_dict = get_wn_dict(args.wordnet_file)
            #drs, pp_dict = wordnet_to_conc(drs, wn_dict, pp_dict)

        # Then remove certain clauses (roles, operators, concepts) if they occur too often
        drs, pp_dict = remove_clauses_by_freq(drs, args.remove_concepts, args.remove_roles_op, idx, pp_dict)

        # Then restore the variables in the correct way
        drs, pp_dict = restore_variables(drs, args.var, idx, pp_dict)

        # Fix some easy-to-fix errors regarding REF clauses
        drs, pp_dict = easy_fixes(drs, idx, pp_dict)

        # If we want, we can try to automatically fix word senses
        if senses:
            drs, pp_dict = fix_word_senses(drs, idx, senses, pp_dict)

        # Now add default for DRSs that are still invalid by doing the more complicated semantic format check (referee)
        if not args.no_referee:
            drs, pp_dict = extensive_format_check(drs, signature, args.fix, idx, pp_dict)

        # Save final DRS
        drss.append([" ".join(c) for c in drs])

    # Write the postprocessed, valid output
    write_list_of_lists(drss, args.output_file)

    # Print some final error statistics
    print("\nError statistics:\n")
    for error in possible_repairs[0:-2]:
        print("{0} repairs needed for error-type: {1}".format(pp_dict[error], error))
    for error in possible_repairs[-2:]:
        print("{0} dummies inserted for {1}".format(pp_dict[error], error))
