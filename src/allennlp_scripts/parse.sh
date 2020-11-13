#!/bin/bash

# Parse raw text with an AllenNLP model
# Note: this script does not work when using multiple encoders
# Arguments: $1: input raw file (not tokenized!)
#            $2: model file
#            $3: target vocab


set -eu -o pipefail
raw_file=$1
cur_model=$2
vocab_file=$3

# Again, we read from settings.sh
source src/allennlp_scripts/settings.sh
# Export paths to be sure
export PYTHONPATH=${DRS_GIT}/evaluation/:${PYTHONPATH}
export PYTHONPATH=${NEURAL_GIT}/src/:${PYTHONPATH}

# Put raw text in format we read with our dataset reader, i.e. add dummy DRS after each line
alp_file=${raw_file}.alp
cp $raw_file $alp_file
TAB=$'\t'
sed -e "s/$/${TAB}Dummy/" -i $alp_file

# Do the predicting
out_file=${raw_file}.drs
allennlp predict $cur_model $alp_file --use-dataset-reader --cuda-device 0 --predictor seq2seq --output-file $out_file $SILENT

# Now do postprocessing, replace ill-formed DRSs by dummies
python $PP_PY --input_file $out_file --output_file ${out_file}.out --sig_file $SIG_FILE --fix --json --sep $SEP -rcl $REMOVE_CLAUSES -m $MIN_TOKENS -voc $vocab_file $no_sep

# Remove temporary .alp file (clean up)
rm $alp_file
