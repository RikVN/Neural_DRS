#!/bin/bash
set -eu -o pipefail

# Check if everything on Github still works as intended
# Mostly small sample experiments to check if there aren't any errors
# I assume everything is run from the $GIT_HOME (Neural_DRS) repo
# Also I assume that ./setup.sh is run before (and that it finished without errors)

cur_dir=$(pwd)
export PYTHONPATH=${cur_dir}/DRS_parsing/evaluation/:${PYTHONPATH}


# Test parsing with downloaded models for OpenNMT
test_opennmt_parse(){
	printf "\n----------------------------------------------\n"
	printf "Test OpenNMT parsing with pretrained models\n"
	# Preprocess test
	python src/preprocess.py -s $SENT_FILE -c feature -r char --sents_only
	cd OpenNMT
	# Parsing test
	../src/opennmt_scripts/parse.sh ../config/opennmt/parse_best_config.sh ${SENT_FILE}.char.sent ${SENT_FILE}.best_gold_only.opennmt.seq.drs ${cur_dir}/models/opennmt/best_gold_only.npz
	../src/opennmt_scripts/parse.sh ../config/opennmt/parse_best_config.sh ${SENT_FILE}.char.sent ${SENT_FILE}.best_gold_silver.opennmt.seq.drs ${cur_dir}/models/opennmt/best_gold_silver.npz
	cd ../
}

# Test preprocessing and training test with sample data for OpenNMT
test_opennmt_train(){
	printf "\n----------------------------------------------\n"
	printf "Test OpenNMT training and parsing\n"
	cd OpenNMT
	../src/opennmt_scripts/preprocess.sh ../config/opennmt/sample.sh
	../src/opennmt_scripts/train.sh ../config/opennmt/sample.sh
	# Check if parsing with your trained model works
	# Obviously output is terrible
	# Model should be in experiments/opennmt/sample/models/model_epoch3*.t7
	model=$(ls ${cur_dir}/experiments/opennmt/sample/models/model_epoch3*t7)
	../src/opennmt_scripts/parse.sh ../config/opennmt/baseline.sh ${SENT_FILE}.char.sent ${SENT_FILE}.sample.seq.drs $model
	cd ../
}

# Test the extracting of the linguistic features for Marian
test_marian_feature_extraction(){
	printf "\n----------------------------------------------\n"
	printf "Testing linguistic feature extraction\n"
	# Begin with extracting all the linguistic features
	./src/marian_scripts/extract_ling_features.sh $SENT_FILE
	# Check if merging the features still works
	python src/merge_tags.py -f ${SENT_FILE}.pos ${SENT_FILE}.dep ${SENT_FILE}.ccg ${SENT_FILE}.lem --char_exts .lem > ${SENT_FILE}.multi
	python src/merge_tags.py -f ${SENT_FILE}.lem --char_exts .lem > ${SENT_FILE}.clem
}


# Test if we can use a pretrained model (needs to be downloaded) to parse raw text file
# Script also takes care of postprocessing
test_marian_parse_raw(){
	printf "\n----------------------------------------------\n"
	printf "Test Marian parsing from pretrained models from raw text\n"
	./src/marian_scripts/parse_raw_text.sh config/marian/best_gold_silver.sh models/marian/best_gold_silver.npz ${SENT_FILE}.marian.best_gold_silver.seq.drs $SENT_FILE ${SENT_FILE}.clem
}


# Test if we can train a (small) Marian model
test_marian_train(){
	printf "\n----------------------------------------------\n"
	printf "Test training a small Marian model\n"
	./src/marian_scripts/pipeline.sh config/marian/sample.sh
}

# Reproduce the F-scores (checks if output files are still there and if counter still works)
# Also the scores should be very similar (at least!) to the ones posted on Github
test_fscores_marian(){
	printf "\n----------------------------------------------\n"
	printf "Test reproducing the F-scores for output files in the output/ folder\n"
	./src/marian_scripts/reproduce_fscores.sh
}

# Test the preprocessing and immediately postprocessing of all PMB data files
# Everything should work without any errors
# Perhaps bit of an overkill to test all files but you never know
test_preprocess_postprocess(){
	printf "\n----------------------------------------------\n"
	printf "Test preprocssing and immediately postprocessing for all possibilities and data sets\n"
	# Set data folder
	data=${cur_dir}/DRS_parsing/data/
	# Loop over the latest release and train/dev/test sets
	for data_set in pmb-3.0.0; do
		for set in train dev test; do
			drs_file="$data/$data_set/gold/${set}.txt"
			sent_file="${drs_file}.raw"
			# Only if file exists
			if [[ -f $drs_file ]] ; then
				echo $drs_file
				## Check if char/word representation works and if casing feature still works
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
					## Without referee
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
	drs_file=${cur_dir}/pmb_exp_data_3.0.0/en/gold_plus_silver/train.txt
	sent_file=${drs_file}.raw
	python src/preprocess.py -i $drs_file -s $sent_file -c feature -v rel -r char --remove_ill --sig_file ${cur_dir}/DRS_parsing/evaluation/clf_signature.yaml
	python src/postprocess.py -i ${drs_file}.char.tgt -o ${drs_file}.restore -s ${cur_dir}/DRS_parsing/evaluation/clf_signature.yaml -v rel
	# Run counter to check if the scores is > 0.995
	printf "Uncomment the next line to run Counter as well\n"
	printf "This can take over 2 hours, so skip for now\n"
	#python ${cur_dir}/DRS_parsing/evaluation/counter.py -f1 ${drs_file}.valid -f2 ${drs_file}.restore -g ${cur_dir}/DRS_parsing/evaluation/clf_signature.yaml -r 10
}

############ MAIN ###############

# Set up a small file to do parsing experiments with
mkdir -p test
SENT_FILE="${cur_dir}/test/test.txt.raw"
printf "This is a test sentence.\nAlso give me a parse for this sentence.\n" > $SENT_FILE

## First test OpenNMT experiments
test_opennmt_parse
test_opennmt_train

### Now test Marian experiments
test_marian_feature_extraction
test_marian_parse_raw
test_marian_train
# This is commented out for 3.0.0 now, since Referee will error
# You have to revert the DRS_parsing repo to v2.2.0 for this to work
#test_fscores_marian

## Test preprocess/postprocess for all data that is made available through the DRS_parsing/ repo
## There shouldn't be any errors
test_preprocess_postprocess

## Also compare for gold_plus_silver data if preprocessing + postprocessing results in F-score of virutally 1.0
## Use the most common setting, char + rel + feature
test_pp_gold_silver



