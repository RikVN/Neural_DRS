#!/bin/bash
set -eu -o pipefail

# Check if general-purpose scripts still work as intended
# Mostly small sample experiments to check if there aren't any errors
# I assume everything is run from the Neural_DRS repo
# Also I assume that ./setup.sh is run before (and that it finished without errors)

cur_dir=$(pwd)
export PYTHONPATH=${cur_dir}/DRS_parsing/evaluation/:${PYTHONPATH}

out_bert_only=output/pmb-3.0.0/en/dev/bert_only/
out_bert_1enc=output/pmb-3.0.0/en/dev/bert_char_1enc/
out_bert_2enc=output/pmb-3.0.0/en/dev/bert_char_2enc/

# Test the preprocessing and immediately postprocessing of all PMB data files
# Everything should work without any errors
# Perhaps bit of an overkill to test all files but you never know
test_preprocess_postprocess(){
	printf "\n----------------------------------------------\n"
	printf "Test preprocessing and immediately postprocessing for all possibilities and data sets\n"
	# Set data folder
	data=${cur_dir}/DRS_parsing/data
	# Loop over the latest release and train/dev/test sets
	for data_set in pmb-3.0.0; do
		for set in train dev test; do
			drs_file="$data/$data_set/gold/${set}.txt"
			sent_file="${drs_file}.raw"
			# Only if file exists
			if [[ -f $drs_file ]] ; then
				echo $drs_file
				# Check if char/word representation works and if casing feature still works
				for rep in char word char_word; do
					for case in normal lower feature; do
						python src/preprocess.py -i $drs_file -s $sent_file -c $case -v rel -r $rep
					done
				done

				# Check if absolute and none still work
				# Also check if postprocessing works for these values
				for var in rel abs none; do
					python src/preprocess.py -i $drs_file -s $sent_file -c feature -v $var -r char
					# Try different things during postprocessing and see if they all work
					python src/postprocess.py -i ${drs_file}.char.tgt -o ${drs_file}.restore -s ${cur_dir}/DRS_parsing/evaluation/clf_signature.yaml -v $var
					# Without referee
					python src/postprocess.py -i ${drs_file}.char.tgt -o ${drs_file}.restore -s ${cur_dir}/DRS_parsing/evaluation/clf_signature.yaml -v $var --no_referee
					# Try to fix wrong DRSs (probably the same as without this feature for gold standard)
					python src/postprocess.py -i ${drs_file}.char.tgt -o ${drs_file}.restore -s ${cur_dir}/DRS_parsing/evaluation/clf_signature.yaml -v $var --fix
					# Remove clauses after certain length (pick low amount so it occurs)
					python src/postprocess.py -i ${drs_file}.char.tgt -o ${drs_file}.restore -s ${cur_dir}/DRS_parsing/evaluation/clf_signature.yaml -v $var -rc 4 -rr 4 -rcl 50
					# Try to fix DRS with removal (so it actually occurs for gold)
					python src/postprocess.py -i ${drs_file}.char.tgt -o ${drs_file}.restore -s ${cur_dir}/DRS_parsing/evaluation/clf_signature.yaml -v $var -rc 4 -rr 4 -rcl 50 --fix
					# Add baseline instead of dummy for ill-formed DRSs
					python src/postprocess.py -i ${drs_file}.char.tgt -o ${drs_file}.restore -s ${cur_dir}/DRS_parsing/evaluation/clf_signature.yaml -v $var -rc 4 -rr 4 -rcl 50 --baseline
				done
			fi
		done
	done
}


# Check that preprocessing and then postprocessing also works on gold + silver data
test_pp_gold_silver(){
	printf "\n----------------------------------------------\n"
	printf "Test preprocessing and postprocessing for gold + silver data\n"
	# Also remove ill-formed from the to be tested set
	drs_file=${cur_dir}/data/3.0.0/en/gold_silver/train.txt
	sent_file=${drs_file}.raw
	python src/preprocess.py -i $drs_file -s $sent_file -c feature -v rel -r char --remove_ill --sig_file ${cur_dir}/DRS_parsing/evaluation/clf_signature.yaml
	python src/postprocess.py -i ${drs_file}.char.tgt -o ${drs_file}.restore -s ${cur_dir}/DRS_parsing/evaluation/clf_signature.yaml -v rel
	# Run counter to check if the scores is > 0.995
	printf "Uncomment the next line to run Counter as well\n"
	printf "This can take over 2 hours, so skip for now\n"
	#python ${cur_dir}/DRS_parsing/evaluation/counter.py -f1 ${drs_file}.valid -f2 ${drs_file}.restore -g ${cur_dir}/DRS_parsing/evaluation/clf_signature.yaml -r 10
}

# Check that DRS jury and separate scripts still work
test_drs_jury(){
	printf "\n----------------------------------------------\n"
	printf "Test DRS jury \n"
	mkdir -p $out_bert_only
	mkdir -p $out_bert_1enc
	mkdir -p $out_bert_2enc

	# Test some different options of DRS jury
	python src/drs_jury.py --folders ${out_bert_only} ${out_bert_1enc} --prefix output -de .txt --working tst/unit/ --names bert_only bert_char_1enc -sf tst/unit/stats.csv
	# More than two folders
	python src/drs_jury.py --folders ${out_bert_only} ${out_bert_1enc} ${out_bert_2enc} --prefix output -de .txt --working tst/unit/ --names bert_only bert_char_1enc bert_char_2enc -sf tst/unit/stats_3.csv
	# Detailed analysis of indices
	python src/drs_jury.py --folders ${out_bert_only} ${out_bert_1enc} --prefix output -de .txt --working tst/unit/ --names bert_only bert_char_1enc -sf tst/unit/stats.csv -a 0 1 2
	
	# Create files with separate F-scores to do tests with
	python DRS_parsing/evaluation/counter.py -f1 ${out_bert_only}output1.txt -f2 data/3.0.0/en/gold/dev.txt -g DRS_parsing/evaluation/clf_signature.yaml -ms_file tst/unit/bert_only/out.idv
	python DRS_parsing/evaluation/counter.py -f1 ${out_bert_1enc}output1.txt -f2 data/3.0.0/en/gold/dev.txt -g DRS_parsing/evaluation/clf_signature.yaml -ms_file tst/unit/bert_char_1enc/out.idv
	
	# Separate tests of the semtag analysis
	python src/semtag_analysis.py --semtag_file DRS_parsing/parsing/layer_data/gold/en/dev.conll --result_files tst/unit/bert_only/idv/output_idv0 tst/unit/bert_char_1enc/idv/output_idv0 --names bert_only bert_char_1enc -min 5 -m -c
	python src/semtag_analysis.py --semtag_file DRS_parsing/parsing/layer_data/gold/en/dev.conll --result_files tst/unit/bert_only/out.idv tst/unit/bert_char_1enc/out.idv --names bert_only bert_char_1enc -min 5 -c
	
	# Separate test of the senlength plots
	python src/senlen_plot.py --input_files tst/unit/bert_only/out.idv tst/unit/bert_char_1enc/out.idv --sentences DRS_parsing/data/pmb-3.0.0/gold/dev.txt.raw.tok --output_file tst/unit/plot.pdf --names "bert only" "bert + ch (1e)"
	python src/senlen_plot.py --input_files tst/unit/bert_only/out.idv tst/unit/bert_char_1enc/out.idv --sentences DRS_parsing/data/pmb-3.0.0/gold/dev.txt.raw.tok --output_file tst/unit/plot.pdf --names "bert only" "bert + ch (1e)" -noc

	# Separate test of approximate randomization
	python src/approximate_randomization.py -f1 tst/unit/bert_only/out.idv -f2 tst/unit/bert_char_1enc/out.idv -r 1000
}

############ MAIN ###############

# Test preprocess/postprocess for all data that is made available through the DRS_parsing/ repo
# There shouldn't be any errors
test_preprocess_postprocess

# Also compare for gold_silver data if preprocessing + postprocessing results in F-score of virutally 1.0
# Use the most common setting, char + rel + feature
test_pp_gold_silver

# Test DRS jury
test_drs_jury

printf "\n------------------ DONE ----------------------\n"
