#!/usr/bin/env python
# -*- coding: utf8 -*-

'''
Script that preprocess DRS-clause files and puts them in a format for sequence-to-sequence algorithms
Example usage (python3): python preprocess.py -i INPUT_FILE -s SENT_FILE -c feature -v rel -r char
'''

import argparse
import copy
from uts import write_to_file, write_list_of_lists, get_drss, is_operator, between_quotes, op_boxes,  \
                is_role, read_and_strip_file, drs_string_to_list
from clf_referee import check_clf
from clf_referee import get_signature


def create_arg_parser():
    '''Create argument parser'''
    parser = argparse.ArgumentParser()
    # Parameter that are import to set
    parser.add_argument('-i', "--input_file", default='', type=str, help="DRS input-file")
    parser.add_argument("-s", "--sentence_file", default='', type=str, help="Sentence file")
    parser.add_argument("-e", "--extra_files", nargs="*", type=str, help="Extra files, we don't do anything but filter ill-formed from here as well.")
    parser.add_argument("-c", "--casing", default='normal', choices=['normal', 'lower', 'feature'],
                        help="What do we do with casing? Default 'normal' means do nothing")
    parser.add_argument("-v", "--variables", default='rel', choices=['rel', 'abs', 'none'],
                        help="How do we rewrite the variables, relatively (default), absolute or not at all?")
    parser.add_argument("-r", "--representation", default='char', choices=['char', 'word', 'char_word'],
                        help="What is the representation of the source/target: characters (default), words or chars+words?")
    # Whether we want to remove ill-formed DRSs
    # Only use this for training a model, not for dev test sets (though they should be well-formed generally0
    parser.add_argument("-sig", "--sig_file", default='', type=str, help="Signature file for format checking")
    parser.add_argument("-ri", "--remove_ill", action='store_true', help="Remove ill-formed DRSs from the set (need signature as well)")
    # (Boolean) parameters that can influence the process
    parser.add_argument("-so", "--sents_only", action='store_true', help="Only process the sentence file to character-level")
    parser.add_argument("-do", "--drss_only", action='store_true', help="Only process DRS file to char-level")

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
    if args.remove_ill and not args.sig_file:
        raise ValueError("Always specify --sig_file when using --remove_ill")
    if args.sig_file and not args.remove_ill:
        print("WARNING: signature file is specified but doesn't do anything without --remove_ill")
    return args


class PreprocessSentences:
    '''Preprocess the sentences to char-level, word-level of char-word level
       Also rewrite uppercase characters to a feature (or not)'''
    def __init__(self, sentences, casing, representation, separator):
        self.sentences = sentences
        self.casing = casing
        self.representation = representation
        self.sep = separator
        self.case_feature = "^^^"
        self.split_case_feature = " ".join(self.case_feature)
        self.features = ['***', '^^^']

    def do_casing(self):
        '''Decide what we do with the casing of the input sentences here
           Options: normal, lower, feature. Feature would look like this:
           ^^^ tom loves ^^^ mary'''
        if self.casing == 'normal':
            return self.sentences
        elif self.casing == 'lower':
            return [x.lower() for x in self.sentences]
        elif self.casing == 'feature':
            # Add lowercase, but add a feature indicating that it was uppercase before
            return ["".join([self.case_feature + char.lower() if char.isupper() else char for char in sent]) for sent in self.sentences]

    def char_tokenization(self, in_sents):
        '''Do character-level tokenization, i.e. change:
           Tom loves Mary to T o m + l o v e s + M a r y'''
        # Split tokens to char level and separate tokens by separation character
        sents = [" ".join(" ".join(" ".join(x.split()).replace(' ', self.sep)).replace(" ".join(self.sep), self.sep).split()) for x in in_sents]
        # We have to change back uppercase features that got split into individual characters in the previous step
        return [" ".join(x.replace(self.split_case_feature, self.case_feature).split()) for x in sents]

    def char_word_level(self, sents):
        '''Format input in such a way that it contains both character and word-level information
           Input sentences are already in character-level format. For example:
           ^^^ t o m Tom + l o v e s loves + ^^^ m a r y Mary'''
        new_sents = []
        for sent in sents:
            new_str = []
            cur_word = ''
            for char in sent.split():
                if char == self.sep: # word boundary, so add full word we have now
                    new_str.append(cur_word)
                    cur_word = '' # reset current word
                elif char not in self.features:
                    # Features regarding capitalization are not part of the word
                    cur_word += char
                new_str.append(char)
            # Still have to add the last word
            if cur_word: # Fix last punctuation if necessary
                if cur_word[-1].isalpha():
                    new_str.append(cur_word)
                else:
                    new_str = new_str[0:-1] + [cur_word[0:-1]] + [self.sep] + [new_str[-1]]
            new_sents.append(" ".join(new_str))
        return new_sents


    def preprocess_sents(self):
        '''Preprocess the sentences, e.g. choose tokenization, choose casing method
           and put in character or word-level format'''
        # Add features for casing (possibly)
        sents = self.do_casing()
        # Then put in char/word level output - for word level we don't have to do anything
        if self.representation == 'char':
            sents = self.char_tokenization(sents)
        elif self.representation == 'char_word':
            # First do char and then merge back to words as well
            sents = self.char_tokenization(sents)
            sents = self.char_word_level(sents)
        # AllenNLP format doesn't like unfinished quotes, for some reason, fix here
        sents = self.fix_quotes(sents)
        return sents

    def fix_quotes(self, sents):
        '''AllenNLP doesn't like sentences with mismatched (unaligned) quotes
           If we encounter such a sentence, just remove the last occurence'''
        new_sents = []
        for sent in sents:
            if sent.count('"') % 2 != 0:
                spl_sent = sent.split('"')
                # Only remove last quote
                final_sent = '"'.join(spl_sent[:-1]) + spl_sent[-1]
                new_sents.append(final_sent)
            else:
                new_sents.append(sent)
        return new_sents


class RewriteVariables:
    '''Class the contains the information for rewriting the DRS variables relatively to
       where in the DRS they were introduced, or in an absolute fashion'''
    def __init__(self, drs, rtype):
        self.drs = drs
        self.new_clauses = []
        self.vars_seen = []
        self.boxes_seen = []
        self.cur_var = 0
        self.var_order = self.get_var_order()
        self.box_id = "$"
        self.var_id = "@"
        self.new_id = "NEW"
        self.ref = "REF"
        self.rtype = rtype
        self.abs_disc = {}
        self.abs_box = {}

    def get_var_order(self):
        '''Get order in which disc variables are introduced'''
        return [x[2] for x in self.drs if x[1] == 'REF']

    def get_box_var_rel(self, var):
        '''Get the box rewrite for this variable'''
        if var not in self.boxes_seen:
            self.boxes_seen.append(var)
            # Indicate that we saw a new box
            return '{0}{1}'.format(self.box_id, self.new_id)
        # Else check where we are with seeing boxes, and where the box is we refer to
        cur_box = self.boxes_seen.index(var)
        return self.box_id + str((cur_box - len(self.boxes_seen)) + 1)

    def get_disc_var_rel(self, var):
        '''Return new variable name, use order of introduction to get it'''
        if var not in self.var_order:
            print ("WARNING: {0} not introduced (var_order: {1}), use default {2}0".format(var, self.var_order, self.var_id))
            return self.var_id + "0"
        else:
            ref_value = self.var_order.index(var)
            value = (ref_value - self.cur_var) + 1
            return self.var_id + str(value)

    def get_disc_var_abs(self, key):
        '''Check if item is in dictionary, if so use that, else add to dict
           For absolute naming, discourse variables'''
        if key not in self.abs_disc:
            item = self.var_id + str(len(self.abs_disc))
            self.abs_disc[key] = item
            return item
        return self.abs_disc[key]

    def get_box_var_abs(self, key):
        '''Check if item is in dictionary, if so use that, else add to dict
           For absolute naming, box variables'''
        if key not in self.abs_box:
            item = self.var_id + str(len(self.abs_box))
            self.abs_box[key] = item
            return item
        return self.abs_box[key]

    def get_disc_var(self, var):
        '''Helper function for getting correct discourse variable'''
        if self.rtype == "rel":
            return self.get_disc_var_rel(var)
        return self.get_disc_var_abs(var)

    def get_box_var(self, var):
        '''Helper function for getting correct boxer variable'''
        if self.rtype == "rel":
            return self.get_box_var_rel(var)
        return self.get_box_var_abs(var)

    def rewrite_length_three(self, cur_clause):
        '''Rewrite clauses of length 3, including, importantly, REFs'''
        # Rewrite first box variable
        first_var = self.get_box_var(cur_clause[0])
        # REF is a special case, it introduces a variable for relative renaming
        if cur_clause[1] == 'REF' and self.rtype == "rel":
            self.new_clauses.append([first_var, cur_clause[1]])
            self.cur_var += 1 # saw a new var, so increase cur_var
        # item is in op_boxes, so second item is a box
        elif cur_clause[1] in op_boxes:
            second_var = self.get_box_var(cur_clause[2])
            self.new_clauses.append([first_var, cur_clause[1], second_var])
        else: # Otherwise it is (or should be) a discourse variable
            second_var = self.get_disc_var(cur_clause[2])
            self.new_clauses.append([first_var, cur_clause[1], second_var])

    def rewrite_length_four(self, cur_clause):
        '''Rewrite clauses of length 4, only rewrites, no introductions'''
        first_var = self.get_box_var(cur_clause[0])
        second_var, third_var = cur_clause[2], cur_clause[3] #defaults
        # Only rewrite items that are not between quotes (so variables)
        if not between_quotes(cur_clause[2]):
            if cur_clause[1] in op_boxes:
                second_var = self.get_box_var(cur_clause[2])
            else:
                second_var = self.get_disc_var(cur_clause[2])
        # Now for the third variable
        if not between_quotes(cur_clause[3]):
            if cur_clause[1] in op_boxes + ["PRP"]:
                third_var = self.get_box_var(cur_clause[3])
            else:
                third_var = self.get_disc_var(cur_clause[3])
        self.new_clauses.append([first_var, cur_clause[1], second_var, third_var])

    def rewrite_variables(self):
        '''Rewrite the variable in a relative manner'''
        # For none, just return the drs (basically do nothing)
        if self.rtype == "none":
            return self.drs
        for cur_clause in self.drs:
            # Clause has 3 items
            if len(cur_clause) == 3:
                self.rewrite_length_three(cur_clause)
            # Clause has 4 items, no introduction, only rewrites
            else:
                self.rewrite_length_four(cur_clause)
        return self.new_clauses


def char_level_drs(new_clauses, sep):
    '''Return to string format, use char-level for concepts'''
    return_strings = []
    keep_word = ['"now"', '"speaker"', '"hearer"', '"+"']
    for cur_clause in new_clauses:
        ret_str = ''
        for idx, item in enumerate(cur_clause):
            if between_quotes(item) and cur_clause[1] == 'Name' and idx == 3:
                item = " ".join(item)
            # Items between quotes are characters, except the ones in keep_word
            elif between_quotes(item) and item not in keep_word:
                item = " ".join(cur_clause[idx])
            elif idx == 1 and not is_operator(item) and not is_role(item):
                # Concepts and roles are kept as is
                item = " ".join(item)
            ret_str += ' ' + item + ' ' + sep
        return_strings.append(" ".join(ret_str.rstrip(sep).strip().split()))
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


def word_level_drs(new_clauses, sep):
    '''Return to string-format, keep word-level for concepts'''
    return_strings = []
    for cur_clause in new_clauses:
        ret_str = ''
        for item in cur_clause:
            ret_str += ' ' + item + ' '
        return_strings.append(" ".join(ret_str.rstrip(sep).strip().split()))
    return return_strings


def filter_file_by_idx(in_file, remove_idxs):
    '''Only keep lines of file not in remove_idxs'''
    keep_sents = []
    for idx, line in enumerate(open(in_file, 'r')):
        if idx not in remove_idxs:
            keep_sents.append(line.strip())
    return keep_sents


def is_well_formed_drs(drs, signature):
    '''Return true/false for whether a DRS is well-formed'''
    try:
        _ = check_clf(drs, signature, v=0)
        return True
    except RuntimeError:
        return False


def remove_ill_formed_drss(drss, signature_file):
    '''Remove ill-formed DRSs from a set of DRSs'''
    # Get signature to do the checking
    signature = get_signature(signature_file)

    # Loop over DRSs and only keep valid ones
    new_drss, remove_idxs = [], []
    for idx, drs in enumerate(drss):
        if is_well_formed_drs([tuple(d) for d in drs_string_to_list(drs)], signature):
            new_drss.append(drs)
        # DRS invalid, ignore
        else:
            remove_idxs.append(idx)
    return new_drss, remove_idxs


def rewrite_drss(drss, variable_type, representation, sep):
    '''Rewrite all the variables in the DRS to a relative or absolute representation (or do nothing)
       Also put the DRS in the correct format: character of word-level'''
    rewritten_drss, var_drss = [], []
    for drs in drss:
        # Remove comments and split
        drs = drs_string_to_list(drs)
        # Sanitze DRS variables, sometimes e.g. t1 can be twice introduced by a REF
        drs = sanitize_variables(drs)
        # Rewrite the variables
        rewritten_drs = RewriteVariables(drs, variable_type).rewrite_variables()
        var_drss.append([" ".join(x) for x in rewritten_drs])
        # Put in correct representation
        processed_drs = word_level_drs(rewritten_drs, sep) if representation == 'word' else char_level_drs(rewritten_drs, sep)
        # Insert special clause separation character
        rewritten_drss.append(" *** ".join(processed_drs))
    return rewritten_drss, var_drss


def write_sentences_and_extra_files(sents, remove_idxs, remove_ill, extra_files, sentence_file, char_sent_ext):
    '''Filter extra files and sentenc by ill-formed, and write to file'''
    if remove_ill:
        sents = [s for idx, s in enumerate(sents) if idx not in remove_idxs]
        # Also check the extra files here, we only keep the indices not in remove_idxs
        if extra_files:
            for extra_file in extra_files:
                write_to_file(filter_file_by_idx(extra_file, remove_idxs), extra_file + '.fil')
    write_to_file(sents, sentence_file + char_sent_ext)


if __name__ == "__main__":
    args = create_arg_parser()

    remove_idxs = []
    # First do the sentences
    if not args.drss_only:
        sents = PreprocessSentences(read_and_strip_file(args.sentence_file), args.casing, args.representation, args.sep).preprocess_sents()

    # Check if we do the DRS file as well
    if not args.sents_only:
        drss = get_drss(args.input_file)

        # Check if we ignore ill-formed DRSs perhaps
        # Keep track of the idxs we remove so we can perhaps fix sentences as well
        if args.remove_ill:
            drss, remove_idxs = remove_ill_formed_drss(drss, args.sig_file)
            print("{0} DRSs ignored because they were invalid (referee)".format(len(remove_idxs)))
            # Write all the current valid ones to a file as well
            write_list_of_lists(drss, args.input_file + args.valid_drs_ext)

        # Rewrite the variables and put in char/word level format
        rewritten_drss, var_drss = rewrite_drss(drss, args.variables, args.representation, args.sep)

        # Write all output files we want to keep, input to model and human readable var format
        write_to_file(rewritten_drss, args.input_file + args.char_drs_ext)
        write_list_of_lists(var_drss, args.input_file + args.var_drs_ext)

    # Print sentences all the way at the end, because we might want to remove certain sents by idx
    # because their DRS was ill-formed (which we don't check until later). Do that check here
    if not args.drss_only:
        write_sentences_and_extra_files(sents, remove_idxs, args.remove_ill, args.extra_files, args.sentence_file, args.char_sent_ext)
