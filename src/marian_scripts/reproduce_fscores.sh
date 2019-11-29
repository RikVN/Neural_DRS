#!/bin/bash
# Reproce the Marian F-scores for all the output files added in the Github repository (best_gold_only and best_gold_silver)
# Works for the dev/test sets in PMB 2.2.0
set -eu -o pipefail

# Get folder information from config as always
source config/marian/default_config.sh
export PYTHONPATH=${GIT_HOME}DRS_parsing/evaluation/:${PYTHONPATH}

GOLD="${GIT_HOME}DRS_parsing/data/pmb-2.2.0/gold/"
OUTPUT="${GIT_HOME}/output/pmb-2.2.0/"

# Loop over dev/test and over best_gold_only and best_gold_silver
# Also loop over the 5 different output files there to do Counter with
for set in dev test; do
	echo
	for model in marian_best_gold_silver marian_best_gold_only ; do
		for run in 1 2 3 4 5; do
			# Run Counter with the original gold standard to get the F/P/R scores
			python $COUNTER -f1 ${OUTPUT}$set/$model/output${run}.seq.drs.res -f2 ${GOLD}${set}.txt -prin -r 25 --signature $sig_file $ill > ${OUTPUT}$set/$model/eval${run}.txt
		done
		# After the 5 runs, calculate the average score of the experiment and save
		python $AVERAGE_PY -f ${OUTPUT}$set/$model/
		# For convenience also print the F-score
		# If this hacky method doesn't work somehow just check the avg_scores.txt files
		f_score=$(head -6 ${OUTPUT}$set/$model/avg_scores.txt | tail -1 | cut -d ' ' -f3)
		echo "Model $model on the $set set: F-score of $f_score"
	done

	# Also show the performance of baseline models
	for baseline in best_opennmt boxer sim_spar spar; do
		python $COUNTER -f1 ${OUTPUT}$set/${baseline}.txt -f2 ${GOLD}${set}.txt -prin -r 25 --signature $sig_file $ill > ${OUTPUT}$set/${baseline}.eval
		# Again hacky method to also print the F-scores from the terminal
		f_score=$(grep "F-score  :" ${OUTPUT}$set/${baseline}.eval | cut -d ' ' -f4)
		echo "Model $baseline on $set set: F-score of $f_score"
	done
done


