#!/bin/bash
set -eu -o pipefail

# Test if Marian works as intended.
# I assume everything is run from the Neural_DRS repo
# Also I assume that ./setup.sh is run before (and that it finished without errors)

# Test if we can use a pretrained model (should be downloaded) to parse raw text file
# Script also takes care of postprocessing
test_marian_parse_raw(){
	printf "\n----------------------------------------------\n"
	printf "Test Marian parsing from pretrained models from raw text\n"
	./src/marian_scripts/parse_raw_text.sh config/marian/best_gold_silver.sh models/marian/best_gold_silver.npz ${SENT_FILE}.marian.best_gold_silver.seq.drs $SENT_FILE ${SENT_FILE}.feat.clem
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

# Test the extracting of the linguistic features for Marian
test_marian_feature_extraction(){
	printf "\n----------------------------------------------\n"
	printf "Testing linguistic feature extraction\n"
	# Begin with extracting all the linguistic features
	./src/marian_scripts/extract_ling_features.sh $SENT_FILE
	# Check if merging the features still works
	python src/merge_tags.py -f ${SENT_FILE}.feat.pos ${SENT_FILE}.feat.dep ${SENT_FILE}.feat.ccg ${SENT_FILE}.feat.lem --char_exts .feat.lem > ${SENT_FILE}.multi
	python src/merge_tags.py -f ${SENT_FILE}.feat.lem --char_exts .feat.lem > ${SENT_FILE}.feat.clem
}

############ MAIN ###############

cur_dir=$(pwd)
# Set up a small file to do parsing experiments with
mkdir -p test
SENT_FILE="${cur_dir}/test/test.txt.raw"
printf "This is a test sentence.\nAlso give me a parse for this sentence.\n" > $SENT_FILE

# Test Marian experiments
test_marian_feature_extraction
test_marian_parse_raw
test_marian_train

# This is commented out for 3.0.0 now, since Referee will error
# You have to revert the DRS_parsing repo to v2.2.0 for this to work
#test_fscores_marian
