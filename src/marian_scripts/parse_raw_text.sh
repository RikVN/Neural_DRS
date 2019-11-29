#!/bin/bash
set -eu -o pipefail

# Use a pretrained Marian model to parse raw text
# Note that in the config file $VOCAB_FOR_PARSE should be set to your vocab(s)

# Arguments:
#		$1 : config file of the pretrained model
#       $2 : actual pretrained model to use for parsing
#       $3 : output file
#   $4 - $n: input file(s) - should be multiple for multi-src models

# Always load default settings from config file here
source config/marian/default_config.sh
export PYTHONPATH=${GIT_HOME}DRS_parsing/evaluation/:${PYTHONPATH}

# First command line argument is the config file with specific settings -- it overrides settings in default_config.sh if added
source $1

# Set better variable names
model="$2"
output_file="$3"

# The first input we preprocess to the desired representation that we read from the config files
# The other representations should already be in right format! ($5 and after)
python $PREPROCESS_PYTHON -so --sentence_file $4 --casing $casing --representation $representation --variables $var_rewrite --char_drs_ext $char_tgt_ext --char_sent_ext $char_sent_ext --var_drs_ext $var_drs_ext
sent_char="${4}$char_sent_ext"
input_files="$sent_char ${@:5}"

# Do actual parsing here
${MARIAN_HOME}marian-decoder $VOCAB_FOR_PARSE -w $workspace --log ${output_file}.log --log-level $log_level --seed $RANDOM -m $model --type $model_type -i $input_files -b $beam_size -n $norm $allow_unk $n_best --max-length $max_length --max-length-factor $max_length_factor -d $gpuid --mini-batch $mini_batch > $output_file

# Postprocess the DRS
output_pp="${output_file}.res"
log_pp="${output_pp}.log"
python $POSTPROCESS_PY -i $output_file -o $output_pp -v $var_rewrite -s $sig_file -rcl $remove_clauses -se $sep $fix > $log_pp
