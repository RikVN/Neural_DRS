#!/usr/bin/env python
# -*- coding: utf8 -*-

'''
Script that postprocesses DRS clauses produced by a neural seq2seq parser
Example usage (python3): python postprocess.py -i INPUT_FILE -o OUTPUT_FILE -v rel -s clf_signature.yaml
'''

import argparse
import os
import re
from clf_referee import check_clf, get_signature
from uts import write_list_of_lists, op_boxes, between_quotes, is_concept, get_first_arg_boxes
from uts import remove_by_first_arg_box, remove_comments, read_allennlp_json_predictions
from utils_counter import dummy_drs, spar_drs


def create_arg_parser():
    parser = argparse.ArgumentParser()
    # Input, output and signature files
    parser.add_argument("-i", "--input_file", required=True, type=str, help="Input file with output of a (neural) DRS parser")
    parser.add_argument("-o", "--output_file", required=True, type=str, help="Output file we write the restored DRSs to")
    parser.add_argument("-s", "--sig_file", default='', type=str, help="Signature file for format checking")
    # Arguments that are important to set, has to match the preprocessing steps
    parser.add_argument("-v", "--var", default='rel', choices=['rel', 'abs', 'none'],
                        help="How do we rewrite the variables, relatively (default), absolute or not necessary?")
    parser.add_argument("-se", "--sep", default='|||', type=str, help="Space-separator used")
    parser.add_argument("-ns", "--no_sep", action="store_true", help="No space-separator used (word-based input)")
    # For AllenNLP experiments these settings are important, vocab and specify that we have to read JSON
    parser.add_argument("-j", "--json", action='store_true', help="Input file is in JSON format (AllenNLP)")
    parser.add_argument("-voc", "--vocab", type=str, help="Vocab of AllenNLP experiment, only necessary when using --json as well")
    parser.add_argument("-m", "--min_tokens", type=int, default=20,
                        help="Minimum amount of tokens (only for AllenNLP exp with --json). If not enough tokens we take different beam answer")
    # Perhaps you don't want to replace ill-formed by a dummy, use this argument then (either to not replace, or to give back a baseline DRS)
    parser.add_argument("-n", "--no_referee", action="store_true", help="Don't do referee - just give back output")
    parser.add_argument("-b", "--baseline", action='store_true', help="Add baseline DRS instead of dummy DRS when DRS is invalid")
    # We can perform a number of (easy) fixes to either fix ill-formed DRSs, or to cut-off very long DRSs,
    # or remove too frequent roles/operators/concepts, or add an existing word sense instead of strange one
    parser.add_argument("-f", "--fix", action='store_true',
                        help="Try to fix DRSs for which referee returned 'subordinate relation has a loop' ")
    parser.add_argument("-fd", "--fix_disc", action='store_true', help="Try to fix DRSs for which referee returned 'Boxes are disconnected' ")
    parser.add_argument("-fs", "--fix_senses", default='', type=str,
                        help="If added, it's a file with a list of training set words + senses in this format: count word sense. We use it to fix word senses")
    parser.add_argument("-rc", "--remove_concepts", type=int, default=0,
                        help="Remove concepts that occur more often than X times (default 0 means no removal)")
    parser.add_argument("-rr", "--remove_roles_op", type=int, default=0,
                        help="Remove roles and operators that occur more often than X times (default 0 means no removal)")
    parser.add_argument("-rcl", "--remove_clauses", type=int, default=0,
                        help="Simply remove all clauses after this number (default 0 means no removal)")
    args = parser.parse_args()
    # Validate the arguments
    if (args.remove_concepts == 0 or args.remove_roles_op == 0) and (args.remove_concepts > 0 or args.remove_roles_op > 0):
        raise ValueError("Either have --remove_concepts AND --remove_roles > 0, or have both at 0")
    if args.input_file == args.output_file:
        raise ValueError("Input and output file are the same")
    if args.json and not args.vocab:
        raise ValueError("Always specify --vocab when doing an AllenNLP experiment using --json")
    return args


class PostprocessValues:
    '''Class with some initial postprocess values that get used throughout the experiment'''
    def __init__(self, fix_senses, sig_file, input_file, vocab, min_tokens, do_json, remove_clauses,
                 remove_roles_op, remove_concepts, sep, no_sep, var, baseline, fix, fix_disc, no_referee):
        # Explanation of the error types:
        # unknown: number of clauses removed that contained the UNKNOWN token
        # remove: number of clauses removed because --remove_clauses was used
        # frequency-rolesop: number of clauses removed because --remove_roles_op was used
        # frequency-name: number of clauses removed because --remove_concepts was used (includes names)
        # frequency-conc: number of clauses removed because --remove_concepts was used
        # variables: number of times a variables made an impossible reference (e.g. @3 for the last var)
        # wrong arity: number of times a clause had a wrong (ill-formed) arity and was therefore ignored
        # no-sense: number of clauses that contained a concept, but no sense, insert default n.01 sense
        # no-ref: disc var was not introduced, add REF
        # spurious-ref: disc var was introduced by REF but never used, remove REF clause
        # sense: number of senses we fixed when using --fix_senses
        # sub-loop: number of times we fixed the subordinate relation has a loop problem (--fix)
        # boxes disconnected: number of times we fixed the disconnected boxes problem (--fix_disc)
        self.possible_repairs = ["unknown", "remove", "frequency-rolesop", "frequency-name", "double",
                                 "frequency-conc", "variables", "wrong arity", "no-sense", "no-ref", "spurious-ref",
                                 "sense", "sub loop", "boxes disconnected"]
        self.dummies = ["dummies-pp", "dummies-ref"]
        self.pp_dict = {}
        for key in self.possible_repairs + self.dummies:
            self.pp_dict[key] = []

        # Other settings
        self.senses = [x.split() for x in open(fix_senses, 'r')] if args.fix_senses and os.path.isfile(fix_senses) else None
        self.signature = get_signature(sig_file) if sig_file and os.path.isfile(args.sig_file) else None
        self.lines = read_allennlp_json_predictions(input_file, vocab, min_tokens) if do_json else [x.strip() for x in open(args.input_file, 'r')]
        self.rm_clauses = remove_clauses
        self.rm_roles_op = remove_roles_op
        self.rm_concepts = remove_concepts
        self.sep = sep
        self.no_sep = no_sep
        self.var = var
        self.baseline = baseline
        self.fix = fix
        self.fix_disc = fix_disc
        self.no_referee = no_referee
        self.box_id = 'b'
        self.var_id = 'x'
        # Counter that we use to keep track of current DRS idx
        self.cur_idx = -1

    def print_stats(self):
        '''Print statistics over postprocessing fixes'''
        print ("Number of fixes per type:\n")
        for key in self.possible_repairs:
            print("{0}: {1}".format(key, len(self.pp_dict[key])))
        print ("\nNumber of dummies per type:\n")
        for key in self.dummies:
            print("{0}: {1}".format(key, len(self.pp_dict[key])))


class RestoreVariables:
    '''Class with some initial postprocess values that get used throughout the experiment'''
    def __init__(self, drs, pp_info):
        self.drs = drs
        self.cur_var = 0
        self.cur_box = 0
        self.box_ident = '$'
        self.var_ident = '@'
        self.new_clauses = []
        self.pp_info = pp_info
        self.var_type = self.pp_info.var
        self.new_box = "$NEW"
        self.box_char = "b"
        self.disc_char = "x"
        self.ref = "REF"
        self.default_sense = '"n.01"'
        self.extra_third_var_boxes = ["PRP"]
        self.var_list = self.order_of_ref_introduction()
        self.box_list = self.get_box_order()
        self.abs_box_dict = {}
        self.abs_disc_dict = {}

    def get_box_order(self):
        '''Number and order of boxes for relative rewriting'''
        box_order = []
        for clause in self.drs:
            for item in clause.split():
                if item == self.new_box:
                    box_order.append(self.box_char + str(len(box_order) + 1))
        return box_order

    def order_of_ref_introduction(self):
        '''Get the order in which REFs are introduced'''
        return [self.disc_char + str(idx+1) for idx in range(len([1 for idx, x in enumerate(self.drs) if len(x.split()) > 1 and x.split()[1] == self.ref]))]

    def get_var_num(self, var):
        '''Strip @ from @-1 and @2 etc, return 0 if it fails'''
        try:
            return int(var[1:])
        except:
            return 0

    def get_abs_var_disc(self, key):
        '''Get absolute variable for discourse var'''
        if key not in self.abs_disc_dict:
            item = self.disc_char + str(len(self.abs_disc_dict))
            self.abs_disc_dict[key] = item
            return item
        else:
            return self.abs_disc_dict[key]

    def get_abs_var_box(self, key):
        '''Get absolute variable for box var'''
        if key not in self.abs_box_dict:
            item = self.box_char + str(len(self.abs_box_dict))
            self.abs_box_dict[key] = item
            return item
        else:
            return self.abs_box_dict[key]

    def get_variable(self, var, is_box):
        '''Helper function to get the right variable for absolute/relative restore'''
        if self.var_type == "rel":
            return self.get_rel_var(var, is_box)
        elif is_box: # Always absolute here
            return self.get_abs_var_box(var)
        return self.get_abs_var_disc(var)

    def get_rel_var(self, item, is_box):
        '''Get new variable name for references such as @-1 and @1'''
        # Check if we box variables or disc variables
        cur_list = self.box_list if is_box else self.var_list
        cur_ident = self.box_ident if is_box else self.var_ident
        cur_v = self.cur_box if is_box else self.cur_var

        if item == cur_ident + 'NEW':
            # Deal with newly introduced variables that say new
            return_var = cur_list[cur_v]
            if is_box:
                self.cur_box += 1
            else:
                self.cur_var += 1
            return return_var

        # Not new, find reference
        ref_num = self.get_var_num(item)
        num = cur_v + ref_num - 1
        if num < 0:
            # Negative numbers are impossible, closest is then 0, so use that
            num = 0

        # Get variable we are currently referring to
        try:
            second_var = cur_list[num]
        except: # Num larger than length of list, take last item
            self.pp_info.pp_dict["variables"].append(self.pp_info.cur_idx)
            second_var = cur_list[-1]
        return second_var

    def rewrite_length_two_three(self, cur_clause):
        '''Rewrite clauses of length two or three'''
        first_var = self.get_variable(cur_clause[0], True)
        if cur_clause[1] == self.ref and self.var_type == "rel":
            # REF is only special case for relative rewriting
            self.cur_var += 1
            self.new_clauses.append([first_var, self.ref, self.pp_info.var_id + str(self.cur_var)])
        elif cur_clause[1] in op_boxes:
            second_var = self.get_variable(cur_clause[2], True)
            self.new_clauses.append([first_var, cur_clause[1], second_var])
        else:
            # Just treat second item as normal disc variable
            second_var = self.get_variable(cur_clause[2], False)
            self.new_clauses.append([first_var, cur_clause[1], second_var])

    def rewrite_length_four(self, cur_clause):
        '''Rewrite clauses of length four in relative manner'''
        first_var = self.get_variable(cur_clause[0], True)
        second_var, third_var = cur_clause[2], cur_clause[3] # defaults
        # First do second variable, then do third variable
        if not between_quotes(cur_clause[2]):
            second_var = self.get_variable(cur_clause[2], cur_clause[1] in op_boxes)
        if not between_quotes(cur_clause[3]):
            third_var = self.get_variable(cur_clause[3], cur_clause[1] in op_boxes + self.extra_third_var_boxes)

        # Fix sense if model didn't produce one
        if is_concept(cur_clause[1]) and not between_quotes(cur_clause[2]):
            self.pp_info.pp_dict["no-sense"].append(self.pp_info.cur_idx)
            second_var = self.default_sense
        # Add the final clause
        self.new_clauses.append([first_var, cur_clause[1], second_var, third_var])

    def rewrite_variables(self):
        '''Rewrite the variables from relative/absolute naming to original naming'''
        for clause_string in self.drs:
            try:
                cur_clause = clause_string.split()
                if len(cur_clause) in [2, 3]: # Clause has 2 or 3 items
                    self.rewrite_length_two_three(cur_clause)
                elif len(cur_clause) == 4: # Clause has 4 items
                    self.rewrite_length_four(cur_clause)
                else: # Clause has wrong length, ignore
                    self.pp_info.pp_dict["wrong arity"].append(self.pp_info.cur_idx)
            except:
                self.pp_info.pp_dict["variables"].append(self.pp_info.cur_idx)
        return self.new_clauses


def default_drs(baseline, list_output=True):
    '''Return a default DRS, either dummy or SPAR'''
    if baseline:
        return spar_drs(list_output=list_output)
    return dummy_drs(list_output=list_output)


def two_spaces(item, prev_item, sep):
    '''Check two items are both the separator'''
    return item == sep and prev_item == sep


def replace_double_space(line, sep):
    '''If we accidentally output two spaces for a role, output the previous variable two times
       This way the matching always goes wrong (so the mistake is punished), but we do have a valid DRS still'''
    new_list = []
    if line.strip(): # Catch empty line
        spl_line = line.split()
        # If first item is a space we just remove it
        if spl_line[0] == sep:
            spl_line = spl_line[1:]
        # Remove the two spaces here
        for idx, item in enumerate(spl_line):
            if two_spaces(item, spl_line[idx-1], sep) and len(new_list) > 2:
                # Add previous var again
                new_list.append(new_list[-2])
            else:
                new_list.append(item)
    return " ".join(new_list)


def restore_variables_none(drs, pp_info):
    '''Restore variables when there's nothing to rewrite, i.e. only
       remove comments and check if arity is correct'''
    var_drs = []
    for clause in drs:
        cur_clause = remove_comments(clause)
        if len(cur_clause) in [3, 4]:
            var_drs.append(cur_clause)
        else:
            pp_info.pp_dict["variables"].append(pp_info.cur_idx)
    return var_drs


def restore_variables(drs, pp_info):
    '''Restore the variables of the output DRSs'''
    try:
        # Important difference between relative and absolute descriptions of variables here
        if pp_info.var in ['rel', 'abs']:
            var_drs = RestoreVariables(drs, pp_info).rewrite_variables()
        elif pp_info.var == 'none':
            var_drs = restore_variables_none(drs, pp_info)
    # Something went wrong, add dummy DRS
    except:
        var_drs = [default_drs(pp_info.baseline, list_output=False)]
        pp_info.pp_dict["dummies-pp"].append(pp_info.cur_idx)
    return var_drs


def replace_space_with_concept(line, sep):
    '''Sometimes we output a space where we should have a put a concept or variable
       In case of a concept we just put a default "male", in case of a variable we replace'''
    return line.replace('{0} {0} {0}'.format(sep), '{0} male {0}'.format(sep)).replace('▁', '')


def restore_sep_plus(line):
    '''If we used + as a separator we have to be careful not to remove actual + characters'''
    return line.replace('"+"', 'TMPSAVE').replace(' ', '').replace('+', ' ').replace('TMPSAVE', '"+"')


def remove_unknown(clause_list_init, pp_info):
    '''BERT experiment can have "@@UNKNOWN@@" in a clause (which is invalid), remove those here'''
    clause_list = [clause for clause in clause_list_init if '@@UNKNOWN@@' not in clause]
    if len(clause_list) < len(clause_list_init):
        pp_info.pp_dict["unknown"].append(pp_info.cur_idx)
    return clause_list


def remove_after_idx(clause_list, pp_info):
    '''Remove clauses after a certain amount (if specified)'''
    # Remove clauses after a certain amount (if specified)
    if pp_info.rm_clauses > 0 and len(clause_list) > pp_info.rm_clauses:
        pp_info.pp_dict["remove"].append(pp_info.cur_idx)
        clause_list = clause_list[0:pp_info.rm_clauses]
    return clause_list


def restore_clauses(line, pp_info):
    '''Restore clauses from one-line format with placeholder characters to list of lists with clauses'''
    # Sometimes the model outputs weird spaces, fix those here
    line = replace_space_with_concept(line, pp_info.sep)
    line = replace_double_space(line, pp_info.sep)

    # Check if we have to restore the spaces (char input)
    # For word input we didn't necessarily need it, then do nothing
    if not pp_info.no_sep:
        # For a + separator we have to be careful not to remove a normal +
        if pp_info.sep == '+':
            line = restore_sep_plus(line)
        else:
            line = line.replace(' ', '').replace(pp_info.sep, ' ')

    # Change line to a list of clauses, remove AllenNLP unknown concepts
    clause_list = remove_unknown(line.split('***'), pp_info)
    clause_list = remove_after_idx(clause_list, pp_info)
    return clause_list


def remove_clauses_by_freq(drs, pp_info):
    '''For each DRS, remove certain clauses if they occur too often'''
    if pp_info.rm_concepts > 0:
        drs = remove_concepts(drs, pp_info)
    if pp_info.rm_roles_op > 0:
        drs = remove_roles_operators(drs, pp_info)
    return drs


def is_disc_ref(main_item, item, clause_idx):
    '''Return whether item is discourse variable, given main_item and position in the clause'''
    if main_item == "PRP":
        return clause_idx == 2
    return main_item not in op_boxes and not between_quotes(item)


def get_disc_refs(drs):
    '''Get all discourse referents that occur in non-REF clauses
       Also save corresponding box so we know where to introduce'''
    disc_refs = []
    boxes = []
    for cur_clause in [x for x in drs if x[1] != "REF"]:
        # If the identifier is not in op_boxes we found a discourse referent
        if len(cur_clause) == 3:
            if cur_clause[2] not in disc_refs and is_disc_ref(cur_clause[1], cur_clause[2], 2):
                disc_refs.append(cur_clause[2])
                boxes.append(cur_clause[0])
        else:
            for clause_idx in [2, 3]:
                if cur_clause[clause_idx] not in disc_refs and is_disc_ref(cur_clause[1], cur_clause[clause_idx], clause_idx):
                    disc_refs.append(cur_clause[clause_idx])
                    boxes.append(cur_clause[0])
    return disc_refs, boxes


def add_missing_ref(refs, disc_refs, disc_boxes, drs, pp_info, do_print=False):
    '''Add missing REF clauses to the DRS'''
    for idx, d in enumerate(disc_refs):
        if d not in refs:
            if do_print:
                pp_info.pp_dict["no-ref"].append(pp_info.cur_idx)
            # Simply add REF clause that is missing
            drs.append([disc_boxes[idx], "REF", d])
    return drs


def remove_spurious_refs(clause_refs, disc_refs, drs, pp_info, do_print=False):
    '''Remove REF clauses that were introduced but never referenced'''
    # Remove spurious REF clauses
    for r in clause_refs:
        if r not in disc_refs:
            if do_print:
                pp_info.pp_dict["spurious-ref"].append(pp_info.cur_idx)
            drs = [d for d in drs if d != r[1]]
    return drs


def check_ref_clauses(drs, pp_info, do_print=True):
    '''Check if each discourse referent that is used has a REF clause'''
    refs = [x[2] for x in drs if x[1] == 'REF']                # all discourse referents introduced by REF

    # Save discourse referents found in other non-REF clauses
    disc_refs, disc_boxes = get_disc_refs(drs)

    # Add missing REF clauses & remove spurious REFs
    drs = add_missing_ref(refs, disc_refs, disc_boxes, drs, pp_info, do_print=do_print)
    drs = remove_spurious_refs(refs, disc_refs, drs, pp_info, do_print=do_print)

    # Check if we didn't remove all clauses (can happen with some strange settings, i.e. sample data)
    if not drs:
        if do_print:
            pp_info.pp_dict["dummies-pp"].append(pp_info.cur_idx)
        return default_drs(pp_info.baseline, list_output=True)
    return drs


def check_doubles(drs, pp_info):
    '''Check if there are double clauses, if so, remove them, but keep order'''
    new_drs = []
    for clause in drs:
        if clause in new_drs:
            # keep track of not adding double
            pp_info.pp_dict["double"].append(pp_info.cur_idx)
        else:
            new_drs.append(clause)
    return new_drs


def remove_concepts(drs, pp_info):
    '''Remove all concepts that occur more often than rm_concepts times
       Do the same for names -- they might also loop and occur way too often
       This setting was not used in the TACL paper, but might help for
       parsing longer sentences'''
    new_drs, concs, names = [], [], []
    for clause_string in drs:
        clause = clause_string.split()
        if len(clause) > 1 and is_concept(clause[1]):
            if concs.count(clause[1]) < pp_info.rm_concepts:
                new_drs.append(" ".join(clause))
            else:
                pp_info.pp_dict["frequency-conc"].append(pp_info.cur_idx)
            concs.append(clause[1])
        elif len(clause) > 1 and clause[1] == 'Name' and len(clause) == 4:
            if names.count(clause[3]) < pp_info.rm_concepts:
                new_drs.append(" ".join(clause))
            else:
                pp_info.pp_dict["frequency-name"].append(pp_info.cur_idx)
            names.append(clause[3])
        else:
            new_drs.append(" ".join(clause))
    return new_drs


def remove_roles_operators(drs, pp_info):
    '''Remove all roles AND operators that occur more often than rm_roles_op times
       This setting was not used in the TACL paper, but might help for
       parsing longer sentences'''
    new_drs, roles = [], []
    for clause_string in drs:
        clause = clause_string.split()
        if len(clause) > 1 and clause[1] != 'REF' and clause[1][0].isupper():
            if roles.count(clause[1]) < pp_info.rm_roles_op:
                new_drs.append(" ".join(clause))
            else:
                pp_info.pp_dict["frequency-rolesop"].append(pp_info.cur_idx)
            roles.append(clause[1])
        else:
            new_drs.append(" ".join(clause))
    return new_drs


def sense_occurs(concept, sense, senses):
    '''Check if current sense occurs in the full set of sense'''
    for sns in senses:
        if [concept, sense] == sns[1:3]:
            return True
    return False


def fix_word_senses(drs, pp_info):
    '''Try to automatically fix produced word senses'''
    # Loop over clauses in DRS
    for clause_idx, clause in enumerate(drs):
        if is_concept(clause):
            box, concept, sense, var = clause.split()[0:4]
            # If sense doesn't occur in full set, check if the word occurs with a different sense
            # If true, use that sense instead - so change clause
            if not sense_occurs(concept, sense, pp_info.senses):
                for sns in pp_info.senses:
                    if concept == sns[1]:
                        drs[clause_idx] = " ".join([box, concept, sns[2], var])
                        pp_info.pp_dict["sense"].append(pp_info.cur_idx)
                        break
    return drs


def easy_fixes(drs, pp_info):
    '''Perform some easy output-fixing for trivial errors the model makes'''
    try:
        # Check if there are double clauses (not allowed, so remove them)
        drs = check_doubles(drs, pp_info)
        # Check if each discourse referent that is used also has a REF
        # So removing spurious REFs, or adding them if necessary
        drs = check_ref_clauses(drs, pp_info)
    except:
        drs = default_drs(pp_info.baseline, list_output=False)
        pp_info.pp_dict["dummies-pp"].append(pp_info.cur_idx)
    return drs


def merge_boxes(clf, boxes):
    '''Merge all boxes in list 'boxes' together in a single box'''
    if len(boxes) >= 2:
        # This is the box we will change all boxes to
        main_box = boxes[0]
        new_clf = []
        for clause in clf:
            new_item = []
            for item in clause:
                if item in boxes[1:]:
                    new_item.append(main_box)
                else:
                    new_item.append(item)
            new_clf.append(tuple(new_item))
        return new_clf
    else:
        return clf


def solve_loops(clf, box, pp_info):
    '''Recursive function: simply remove the box from a DRS that returned
       the subordinate relation has a loop error.
       If the new DRS gets a loop error message,
       then simply remove the new box as well (etc)'''
    # If already empty, return False
    if not clf:
        return False

    # First try to merge the offending box with any other box, and see if the DRS is valid now
    boxes = get_first_arg_boxes(clf)
    for b in boxes:
        if box != b:
            new_clf = merge_boxes(clf, [b, box])
            try:
                _ = check_clf(new_clf, pp_info.signature, v=0)
                # No error means the DRS is now valid, so return
                return new_clf
            except RuntimeError as err:
                pass

    # If this is not the case, we remove the offending box
    new_clf = remove_by_first_arg_box(clf, box)

    # Maybe we need to insert or remove REFs again
    new_clf_tmp = check_ref_clauses(new_clf, pp_info, do_print=False)
    new_clf = [tuple(x) for x in new_clf_tmp]

    # Check if the new DRS is valid
    try:
        _ = check_clf(new_clf, pp_info.signature, v=0)
        # No error means the DRS is now valid, so return
        return new_clf
    except RuntimeError as err:
        err_message = str(err)
        # Check the error message, if again a loop is the problem, call this function again
        if 'Subordinate relation has a loop' in err_message:
            box_num = err_message.split('||')[1].split('>')[0].strip()
            # If nothing changed, avoid infinite loops by stopping here
            if new_clf == clf:
                return False
            else:
                # Otherwise try this function again
                new_clf = solve_loops(new_clf, box_num, pp_info)
        # Different error, so approach didn't work, quit
        else:
            return False
    return new_clf


def get_discs_by_boxes(drs, boxes):
    '''Return all discourse variables that are introduced by one of the boxes given in boxes'''
    return [x[2] for x in drs if x[0] in boxes and x[1] == "REF"]


def change_box_in_drs(drs, index, box_var):
    '''Make sure nothing goes wrong with copying, so copy whole DRS here except with
       different box var for the clause at idx index'''
    new_drs = []
    for idx, clause in enumerate(drs):
        if idx == index:
            print ("Changing box", clause[0], "to", box_var)
            new_drs.append([box_var] + clause[1:])
        else:
            new_drs.append(clause)
    return new_drs


def solve_non_connected(drs, boxes1, boxes2, signature):
    '''Try to solve sets of unconnected boxes by changing a discourse variable to a disc var present in a different box'''
    # Introduce variables in one of the other boxes and see if that helps
    for idx, clause in enumerate(drs):
        if clause[1] == "REF" and clause[0] in boxes1:
            for box in boxes2:
                fixed_drs = change_box_in_drs(drs, idx, box)
                try:
                    _ = check_clf([tuple(c) for c in fixed_drs], signature, v=0)
                    return fixed_drs
                except RuntimeError:
                    pass
        elif clause[1] == "REF" and clause[0] in boxes2:
            for box in boxes1:
                fixed_drs = change_box_in_drs(drs, idx, box)
                try:
                    _ = check_clf([tuple(c) for c in fixed_drs], signature, v=0)
                    return fixed_drs
                except:
                    pass
    # If we get here nothing worked, return dummy
    return False


def extensive_format_check(drs, pp_info):
    '''Do a more extensive semantic format check (referee)
       Also try to fix the DRSs, if specified'''
    fixed_drs = False
    try:
        _ = check_clf([tuple(c) for c in drs], pp_info.signature, v=0)
        return drs
    # DRS invalid, replace by dummy or try to fix
    except RuntimeError as err:
        err_message = str(err)
        # Try to fix subordinate loops by just merging/removing the offending box
        if pp_info.fix and 'Subordinate relation has a loop' in err_message:
            err_cat = "sub loop"
            box_num = err_message.split('||')[1].split('>')[0].strip()
            fixed_drs = solve_loops([tuple(c) for c in drs], box_num, pp_info)
        elif pp_info.fix_disc and "Boxes are not connected" in err_message:
            err_cat = "boxes disconnected"
            boxes = re.findall('\{(.*?)\}', err_message)
            fixed_drs = solve_non_connected(drs, boxes[0].replace(',', '').split(), boxes[1].replace(',', '').split(), pp_info.signature)

    # Only get here if DRS was invalid - if we don't have a fixed one, return dummy
    if fixed_drs:
        pp_info.pp_dict[err_cat].append(pp_info.cur_idx)
        return fixed_drs
    elif pp_info.no_referee:
        # Don't want to do referee dummies, return initial DRS
        return drs
    pp_info.pp_dict["dummies-ref"].append(pp_info.cur_idx)
    return default_drs(pp_info.baseline, list_output=True)


def do_postprocess(args):
    '''Main function of the postprocessing'''
    pp_info = PostprocessValues(args.fix_senses, args.sig_file, args.input_file, args.vocab, args.min_tokens, args.json, args.remove_clauses, \
               args.remove_roles_op, args.remove_concepts, args.sep, args.no_sep, args.var, args.baseline, args.fix, args.fix_disc, args.no_referee)

    drss = []
    # Each line is a DRS, loop over them here one-by-one
    for idx, line in enumerate(pp_info.lines):
        pp_info.cur_idx = idx
        # Restore clause format, we now have a list of clauses (list of strings)
        drs = restore_clauses(line, pp_info)

        # Then remove certain clauses (roles, operators, concepts) if they occur too often
        drs = remove_clauses_by_freq(drs, pp_info)

        # Then restore the variables in the correct way
        drs = restore_variables(drs, pp_info)

        # Fix some easy-to-fix errors regarding REF clauses
        drs = easy_fixes(drs, pp_info)

        # If we want, we can try to automatically fix word senses
        if pp_info.senses:
            drs = fix_word_senses(drs, pp_info)

        # Now add default for DRSs that are still invalid by doing the more complicated semantic format check (referee)
        #if not args.no_referee:
        drs = extensive_format_check(drs, pp_info)

        # Save final DRS
        drss.append([" ".join(c) for c in drs])

    # Write the postprocessed, valid output
    write_list_of_lists(drss, args.output_file)
    # Print stats of postprocessing
    pp_info.print_stats()


if __name__ == "__main__":
    args = create_arg_parser()
    do_postprocess(args)
