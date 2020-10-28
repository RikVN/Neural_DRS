#!/bin/bash
set -eu -o pipefail

# Test if OpenNMT works as intended.
# I assume everything is run from the Neural_DRS repo
# Also I assume that ./setup.sh is run before (and that it finished without errors)

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

############ MAIN ###############

cur_dir=$(pwd)
# Set up a small file to do parsing experiments with
mkdir -p test
SENT_FILE="${cur_dir}/test/test.txt.raw"
printf "This is a test sentence.\nAlso give me a parse for this sentence.\n" > $SENT_FILE

# Test OpenNMT experiments
test_opennmt_parse
test_opennmt_train
