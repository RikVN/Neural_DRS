#!/usr/bin/env python
# -*- coding: utf8 -*-

'''
Script that postprocesses DRS clauses produced by a neural seq2seq parser
Example usage (python2): python postprocess.py -i INPUT_FILE -o OUTPUT_FILE -v rel -s clf_signature.yaml
'''


import argparse
import sys
reload(sys)
sys.setdefaultencoding('utf-8') #necessary to avoid unicode errors
from collections import Counter
from clf_referee import check_clf
from clf_referee import get_signature
from uts import *


def create_arg_parser():
	parser = argparse.ArgumentParser()
	parser.add_argument("-i", "--input_file", required=True, type=str, help="Input file")
	parser.add_argument("-o", "--output_file", required=True, type=str, help="Output file")
	parser.add_argument("-v", "--var", default='rel', choices=['rel', 'abs', 'none'], help="How do we rewrite the variables, relatively (default), absolute or not necessary?")
	parser.add_argument("-s", "--sig_file", required=True, type=str, help="Signature file for format checking")
	parser.add_argument("-n", "--no_referee", action="store_true", help="Don't do referee - just give back output")
	parser.add_argument("-rc", "--remove_concepts", type=int, default=0, 
						help="Remove concepts that occur more often than X times (default 0 means no removal). This helps if you parse longer sentences and the parser gets into a loop. \
							  Note that this setting was not used for the TACL paper experiments.")
	parser.add_argument("-rcl", "--remove_clauses", type=int, default=0, 
						help="Simply remove all clauses after this number (default 0 means no removal). This helps if you parse longer sentences and the parser gets into a loop. \
							  Note that this setting was not used for the TACL paper experiments.")
	args = parser.parse_args()
	return args


def dummy_drs(list_output=True):
	'''Return dummy DRS in clause format'''
	if list_output:
		return [['b1', 'REF', 'x1'], ['b1', 'alwayswrongconcept', '"n.01"', 'x1']]
	else:
		return ['b1 REF x1', 'b1 alwayswrongconcept "n.01" x1']


def replace_double_space(line):
	'''If we accidentally output two spaces for a role, output the previous variable two times
	   This way the matching always goes wrong (so the mistake is punished), but we do have a valid DRS still'''
	new_list = []
	spl_line = line.split()
	# If first item is a space we just remove it
	if spl_line[0] == '|||':
		spl_line = spl_line[1:]

	for idx, item in enumerate(spl_line):
		if item == '|||' and spl_line[idx-1] == '|||':
			new_list.append(new_list[-2])
		else:
			new_list.append(item)
	return " ".join(new_list)


def restore_variables(in_drss, var):
	'''Restore the variables of the output DRSs '''
	processed_drss = []
	repairs = 0
	dummies = 0

	for idx, drs in enumerate(in_drss):
		try:
			#Important difference between relative and absolute descriptions of variables here
			if var == 'rel':
				var_drs, cur_repairs = restore_variables_relative(drs, idx+1)
				repairs += cur_repairs
			elif var == 'abs':
				var_drs, repairs = restore_variables_absolute(drs, idx+1)
			elif var == 'none':
				var_drs = []
				for clause in drs:
					cur_clause = clause.split()[0:clause.split().index('%')] if '%' in clause.split() else clause.split()
					if len(cur_clause) in [3,4]:
						var_drs.append(cur_clause)
					else:
						repairs += 1
						print 'DRS {0}: Ignoring clause {1} because of wrong arity'.format(idx, clause) 
		except:
			var_drs = dummy_drs()
			dummies += 1
		processed_drss.append([" ".join(x) for x in var_drs])
	return processed_drss, repairs, dummies



def restore_clauses(file_name, remove_clauses):
	'''Restore clauses from one-line format with placeholder characters to list of lists with clauses'''
	restored = []
	fixes = 0
	## Sometimes we output a space where we should have a put a concept or variable
	## In case of a concept we just put a default "male", in case of a variable we replace
	## it by the same variable already used in the DRS (for some reason it's always the last one that is wrong)
	for idx, line in enumerate(open(file_name, 'r')):
		line = line.replace('||| ||| |||', '||| male |||').replace('▁', '')
		line = replace_double_space(line)
		line = line.replace(' ', '').replace('|||', ' ').split('***')
		# Remove clauses after a certain amount (if specified)
		if remove_clauses > 0:
			if len(line) > remove_clauses:
				print 'DRS {0}: Removing clauses after clause {1} for total length {2}'.format(idx, remove_clauses, len(line))
				fixes += 1
				line = line[0:remove_clauses]
		restored.append(line)
	return restored, fixes


def get_disc_refs(drs):
	'''Get all discourse referents that occur in non-REF clauses'''
	disc_refs = []
	for clause in drs:
		if not clause.strip().startswith('%'):
			cur_clause = clause.split()[0:clause.split().index('%')] if '%' in clause.split() else clause.split()
			# If the identifier is not in op_boxes we found a discourse referent
			if len(cur_clause) == 3:
				if cur_clause[1] not in op_boxes and not between_quotes(cur_clause[2]):
					if cur_clause[2] not in disc_refs:
						disc_refs.append([cur_clause[0], cur_clause[2], cur_clause])
			else: # Clause has 4 items
				#Everything that is not between quotes for item 3/4 is a disc ref, except when it is box variable due to the operator
				if cur_clause[1] not in op_boxes and cur_clause[1] != 'PRP' and not between_quotes(cur_clause[2]):
					if cur_clause[2] not in disc_refs:
						disc_refs.append([cur_clause[0], cur_clause[2], cur_clause])
				if cur_clause[1] not in op_boxes and cur_clause[1] != 'PRP' and not between_quotes(cur_clause[3]):
					if cur_clause[3] not in disc_refs:
						disc_refs.append([cur_clause[0], cur_clause[3], cur_clause])
	return disc_refs


def check_ref_clauses(input_drs, drs_idx):
	'''Check if each discourse referent that is used has a REF clause'''
	drs = [x for x in input_drs if not x.strip().startswith('%')]              # get DRS without comments
	clause_refs = [[x.split()[2], x] for x in drs if x.split()[1] == 'REF']    # get discourse referents with initial clause
	refs = [x.split()[2] for x in drs if x.split()[1] == 'REF']                # all discourse referents introduced by REF

	# Save discourse referents found in other non-REF clauses
	disc_refs = get_disc_refs(drs)
	fixes = 0

	# Add missing REF clauses
	for d in disc_refs:
		if d[1] not in refs:
			# Simply add REF clause that is missing
			add_clause = '{0} REF {1}'.format(d[0], d[1])
			print 'DRS {0}: REF missing for {1} -- Clause: {2} -- Add clause: {3}'.format(drs_idx, d[1], " ".join(d[2]), add_clause)
			drs.append(add_clause)
			fixes += 1

	# Remove spurious REF clauses
	for r in clause_refs:
		if r[0] not in [x[1] for x in disc_refs]:
			print 'DRS {0}: {1} instantiated but never referenced -- Clause: {2} -- removed'.format(drs_idx, r[0], r)
			drs = [d for d in drs if d != r[1]]
			fixes += 1
	return drs, fixes


def check_doubles(drs, drs_idx):
	'''Check if there are double clauses, if so, remove them, but keep order'''
	fixes = 0
	new_drs = []
	for clause in drs:
		if clause.strip().startswith('%'):
			new_drs.append(clause) #keep comments anyway
		else:
			cur_clause = " ".join(clause.split()[0:clause.split().index('%')] if '%' in clause.split() else clause.split())
			if cur_clause in new_drs:
				# Simply remove double clause, so do nothing except printing
				print 'DRS {0}: double clause, remove: {1}'.format(drs_idx, cur_clause)
				fixes += 1
			else:
				new_drs.append(cur_clause)
	return new_drs, fixes


def remove_concepts(drs, rm_concepts, drs_idx):
	'''Remove all concepts that occur more often than rm_concepts times
	   Do the same for names -- they might also loop and occur way too often
	   This setting was not used in the TACL paper, but might help for 
	   parsing longer sentences'''
	new_drs, concs, names = [], [], []
	fixes = 0
	for clause_string in drs:
		clause = clause_string.split()
		if len(clause[1]) == len([a for a in clause[1] if a.islower()]):
			if not concs.count(clause[1]) >= rm_concepts:
				new_drs.append(" ".join(clause))
			else:
				print 'DRS {0}: removing {1} because concept occurs > {2}'.format(drs_idx, clause_string, rm_concepts)
				fixes += 1  
			concs.append(clause[1]) 
		elif clause[1] == 'Name' and len(clause) == 4:
			if not names.count(clause[3]) >= rm_concepts:
				new_drs.append(" ".join(clause))
			else:
				print 'DRS {0}: removing {1} because name occurs > {2}'.format(drs_idx, clause_string, rm_concepts)
				fixes += 1  
			names.append(clause[3]) 
		else:
			new_drs.append(" ".join(clause))
	return new_drs, fixes


def easy_fixes(drss, rm_concepts):
	'''Perform some easy output-fixing for trivial errors the model makes'''
	keep_drss = []
	fixes, dummies, conc_fixes = 0, 0, 0
	for idx, drs in enumerate(drss):
		try:
			# Check if there are double clauses (not allowed, so remove them)
			new_drs, dub_fixes = check_doubles(drs, idx+1)
			# Check if each discourse referent that is used also has a REF
			# So removing spurious REFs, or adding them if necessary
			new_drs, ref_fixes = check_ref_clauses(new_drs, idx+1)
			if rm_concepts > 0:
				new_drs, conc_fixes = remove_concepts(new_drs, rm_concepts, idx+1)
			keep_drss.append(new_drs)
			fixes += (dub_fixes + ref_fixes + conc_fixes)
		except:
			print 'DRS {0}: error when applying "easy" fixes, add dummy DRS'.format(idx+1)
			keep_drss.append(dummy_drs(list_output=False))
			dummies += 1
	return keep_drss, fixes, dummies


def box_variable(key, dic):
	'''Check if item is in dictionary, if so use that, else add to dict'''
	if key not in dic:
		item = 'b' + str(len(dic))
		dic[key] = item
	else:
		item = dic[key]
	return item, dic


def new_var_name(item, var_list, cur_var, clause_string, ident, drs_idx):
	'''Get new variable name for references such as @-1 and @1'''
	if item == ident + 'NEW':
		# Deal with newly introduced variables that say new
		return_var = var_list[cur_var]
		cur_var += 1
		return return_var, 0, cur_var
	else:
		try:
			ref_num = int(item[1:]) # strip @ from @-1 and @2 etc
		except:
			print 'DRS {0}: could not find variable number in {1}, use default 0'.format(drs_idx, item)
			ref_num = 0 #add default 0 if there is no variable in this output

		num = cur_var + ref_num - 1
		repairs_needed = 0
		if num < 0:
			repairs_needed += 1
			num = 0 #negative numbers are impossible, closest is then 0, so use that
			print 'DRS {0}: impossible negative reference for {1}, use default 0'.format(drs_idx, clause_string)

		# Get variable we are currently referring to
		try:
			second_var = var_list[num]
		except: # Num larger than length of list, take last item
			repairs_needed += 1
			second_var = var_list[-1]
			print 'DRS {0}: impossible reference (longer than list-length) for {1}, use default last item'.format(drs_idx, clause_string)
		return second_var, repairs_needed, cur_var


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


def restore_variables_relative(drs, drs_idx):
	'''Restore the dummy variable names we used to actual variables -- relatively'''
	# Get order of variable
	var_list = ['x' + str(idx+1) for idx in range(len([1 for idx, x in enumerate(drs) if len(x.split()) > 1 and x.split()[1] == 'REF']))]
	# Get order of boxes
	box_list = get_box_order(drs)

	# Initial settings
	new_clauses = []
	cur_var, cur_box, repairs_needed = 0, 0, 0 #start value
	box_ident, var_ident = '$', '@'

	for clause_string in drs:
		try:
			cur_clause = clause_string.split()
			# Clause has 2 or 3 items
			if len(cur_clause) in [2, 3]:
				# Restore box variable
				first_var, repairs, cur_box = new_var_name(cur_clause[0], box_list, cur_box, clause_string, box_ident, drs_idx)
				repairs_needed += repairs
				if cur_clause[1] == 'REF':
					# Add REF with x-variable for the REF-case
					cur_var += 1
					new_clauses.append([first_var, 'REF', 'x' + str(cur_var)])
				elif cur_clause[1] in op_boxes: #handle box variables
					second_var, repairs, cur_box = new_var_name(cur_clause[2], box_list, cur_box, clause_string, box_ident, drs_idx)
					repairs_needed += repairs
					new_clauses.append([first_var, cur_clause[1], second_var])
				else:
					print 'DRS {0}: warning, clause {1} gets ignored'.format(drs_idx, clause_string) #clause is invalid by definition, ignore
					repairs_needed += 1
			# Clause has 4 items
			elif len(cur_clause) == 4:
				first_var, repairs, cur_box = new_var_name(cur_clause[0], box_list, cur_box, clause_string, box_ident, drs_idx)
				repairs_needed += repairs
				# Second item is an operator
				if all_upper(cur_clause[1]):
					# Handle second variable
					second_var, third_var = cur_clause[2], cur_clause[3] #defaults
					if not between_quotes(cur_clause[2]):
						if not (cur_clause[1] in op_boxes and cur_clause[1] != 'PRP'):
							second_var, repairs, cur_var = new_var_name(cur_clause[2], var_list, cur_var, clause_string, var_ident, drs_idx)
							repairs_needed += repairs
					# Handle third variable (if there)
					if not between_quotes(cur_clause[3]):
						if cur_clause[1] == 'PRP':
							second_var, repairs, cur_var = new_var_name(cur_clause[2], var_list, cur_var, clause_string, var_ident, drs_idx)
							repairs_needed += repairs
							third_var, repairs, cur_box = new_var_name(cur_clause[3], box_list, cur_box, clause_string, box_ident, drs_idx)
							repairs_needed += repairs
						elif cur_clause[1] in op_boxes: #get box variable
							second_var, repairs, cur_box = new_var_name(cur_clause[2], box_list, cur_box, clause_string, box_ident, drs_idx)
							repairs_needed += repairs
							third_var, repairs, cur_box = new_var_name(cur_clause[3], box_list, cur_box, clause_string, box_ident, drs_idx)
							repairs_needed += repairs
						else:
							third_var, repairs, cur_var = new_var_name(cur_clause[3], var_list, cur_var, clause_string, var_ident, drs_idx)
							repairs_needed += repairs
					new_clauses.append([first_var, cur_clause[1], second_var, third_var])
				# Second item is a role
				elif is_role(cur_clause[1]):
					second_var, repairs, cur_var = new_var_name(cur_clause[2], var_list, cur_var, clause_string, var_ident, drs_idx)
					repairs_needed += repairs
					if not between_quotes(cur_clause[3]):
						third_var, repairs, cur_var = new_var_name(cur_clause[3], var_list, cur_var, clause_string, var_ident, drs_idx)
						repairs_needed += repairs
					else:
						third_var = cur_clause[3]
					new_clauses.append([first_var, cur_clause[1], second_var, third_var])
				# Otherwise it must be a concept (b1 work "v.01" x2)
				else:
					third_var, repairs, cur_var = new_var_name(cur_clause[3], var_list, cur_var, clause_string, var_ident, drs_idx)
					repairs_needed += repairs
					## Put default sense if model did not produce that
					if not between_quotes(cur_clause[2]) and '"' not in cur_clause[2] and cur_clause[2].islower():
						print 'DRS {0}: no sense was added for concept {1}, add default sense'.format(drs_idx, cur_clause[2])
						new_clauses.append([first_var, cur_clause[1], '"n.01"', third_var])
						repairs_needed += 1
					else:
						new_clauses.append([first_var, cur_clause[1], cur_clause[2], third_var])
			else: #clause has wrong length, ignore
				print 'DRS {0}: warning, clause {1} gets ignored'.format(drs_idx, clause_string)
				repairs_needed += 1
		except:
			repairs_needed
			print 'DRS {0}: Error when processing {1} -- ignore clause'.format(drs_idx, clause_string)      
	return new_clauses, repairs_needed


def get_variable(key, dct, ident):
	'''Check if item is in dictionary, if so use that, else add to dict'''
	if key not in dct:
		item = ident + str(len(dct))
		dct[key] = item
	else:
		item = dct[key]
	return item, dct


def restore_variables_absolute(drs, drs_idx):
	'''Restore the dummy variable names we used to actual variables -- absolute'''
	new_clauses = []
	var_dict, box_dict = {}, {}
	box_id, var_id = 'b', 'x'
	repairs = 0

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
				if all_upper(cur_clause[1]):
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
					## Put default sense if model did not produce that
					if not between_quotes(cur_clause[2]) and '"' not in cur_clause[2] and cur_clause[2].islower():
						print 'DRS {0}: no sense was added for concept {1}, add default sense'.format(drs_idx, clause_string)
						repairs += 1
						new_clauses.append([first_var, cur_clause[1], '"n.01"', third_var])
					else:
						new_clauses.append([first_var, cur_clause[1], cur_clause[2], third_var])
		except:
			repairs += 1
			print 'DRS {0}: Error when processing {1} -- ignore clause'.format(drs_idx, clause_string)              
	return new_clauses, repairs


def extensive_format_check(drss_fixed, sig_file):
	'''Do a more extensive semantic format check (referee)'''
	drss_final = []
	signature = get_signature(sig_file)
	error_counter = Counter()
	for clf in drss_fixed:
		try:
			_ = check_clf([tuple(c.split()) for c in clf], signature, v=1)
			drss_final.append(clf)
		except RuntimeError as err_message: #DRS invalid, replace by dummy
			error_counter.update([err_message[0]])
			drss_final.append([" ".join(x) for x in dummy_drs()])
	error_total = sum(error_counter.values())
	print_str = "#wrong = {} ({:.2f}%)".format(error_total, error_total*100/float(len(drss_fixed)))
	for (err, c) in error_counter.most_common():
		print_str += str(c) + ' ' + err + ' '
	return drss_final, print_str, error_total


if __name__ == "__main__":
	args = create_arg_parser()

	# Restore clause format first
	drss, restore_repairs = restore_clauses(args.input_file, args.remove_clauses)

	# Then restore the variables in the correct way
	processed_drss, num_repairs, num_dummies = restore_variables(drss, args.var)
	
	# First fix some easy-to-fix errors regarding REF clauses
	drss_fixed, num_fixes, easy_dummies = easy_fixes(processed_drss, args.remove_concepts)
	
	# Now add default for DRSs that are still invalid by doing the more complicated semantic format check (referee)
	if not args.no_referee:
		drss_final, print_str, error_total = extensive_format_check(drss_fixed, args.sig_file)
	else:
		drss_final = drss_fixed
		error_total = 0
	
	# Write the postprocessed, valid output
	write_list_of_lists(drss_final, args.output_file)

	# Print some final error statistics
	print '\n{0} repairs needed and {1} replaced by dummy for restoring variables'.format(num_repairs, num_dummies)
	print '{0} repairs needed and {1} replaced by dummy for performing easy fixes'.format(num_fixes, easy_dummies)
	if not args.no_referee:
		print '{0} replaced by dummy due to referee check'.format(error_total)
	print '\nTotal: {0} out of {1} DRSs replaced by a dummy and {2} repairs were needed'.format(num_dummies + easy_dummies + error_total, len(drss_final), num_fixes + num_repairs + restore_repairs)
