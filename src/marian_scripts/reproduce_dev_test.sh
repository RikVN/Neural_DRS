#!/bin/bash
set -eu -o pipefail

# Reproduce our results using the downloaded models for baseline_gold_silver
# Parse both the dev and test set 5 times and run counter on results

# Always load default settings from config file here
source config/marian/default_config.sh

# First command line argument is the config file with specific settings -- it overrides settings in default_config.sh if added
source $1

PARSE_RAW="${GIT_HOME}src/marian_scripts/parse_raw_text.sh"
MODEL_FOL="/home/p266548/Documents/DRS_parsing/final_exp_marian/silver/test_baseline/models/test_fol/"
GOLD="${GIT_HOME}DRS_parsing/data/pmb-2.2.0/gold/"
OUTPUT="${GIT_HOME}/output/"

for set in dev test; do
	for model_num in 1; do
		model="${MODEL_FOL}/model${model_num}.npz"
		# Do parsing
		$PARSE_RAW $1 $model $OUTPUT/pmb-2.2.0/$set/marian_baseline_gold_silver/${set}_${model_num}.seq.drs ${GOLD}/${set}.txt.raw.char.sent
		# Do counter
		python $COUNTER -f1 $OUTPUT/pmb-2.2.0/$set/marian_baseline_gold_silver/${set}_${model_num}.seq.drs.res -f2 ${GOLD}${set}.txt -prin -r 25 --signature $sig_file $ill > $OUTPUT/pmb-2.2.0/$set/marian_baseline_gold_silver/${set}_${model_num}.seq.drs.res.eval
	done
	# Average
	python $AVERAGE_PY -f ${OUTPUT}/pmb-2.2.0/$set/marian_baseline_gold_silver/
done
