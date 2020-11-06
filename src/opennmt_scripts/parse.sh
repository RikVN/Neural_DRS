#!/bin/bash
set -eu -o pipefail
### Arguments:
#         $1 : config-file
#         $2 : input-file
#         $3 : output-file
#         $4 : model1
#         $5 : optional: model2 (model3, model4, etc)

source ../config/opennmt/default_config.sh #always load default settings from config file here
source $1 #first command line argument is the config file with specific settings -- it overrides settings in default_config.sh if added

export PYTHONPATH=${GIT_HOME}DRS_parsing/evaluation/:${PYTHONPATH}

# Change if you want no logs
#disable_logs="-disable_logs"
disable_logs=""

# NOTE: specifying multiple models can easily result in out-of-memory errors (on GPU)
# if you are parsing something that is not the small PMB data, be aware that this can happen

# Check if arguments are set -- $2 and $3 are input files and output files
if [ ! -z "$2" ] && [ ! -z "$3" ] && [ ! -z "$4" ]; then
    # Get all models in a single param
    models="${@:4}"
    # Do parsing here
    th translate.lua -src $2 -output $3 -model $models -beam_size $beam_size -max_sent_length $max_sent_length $replace_unk -n_best $n_best -length_norm $length_norm -coverage_norm $coverage_norm -eos_norm $eos_norm $gpuid $disable_logs
    # Postprocess
    python $POSTPROCESS_PY --input_file $3 --output_file $3$res_ext --var $var_rewrite --sig_file $sig_file > $3${res_ext}.log
    python $POSTPROCESS_PY --input_file $3 --output_file ${3}.noref --var $var_rewrite --sig_file $sig_file --no_referee > ${3}.noref.log
else
    echo "Usage: parse.sh CONFIG_FILE INPUT_FILE OUTPUT_FILE MODEL1 [MODEL2] [MODEL3] .."
fi
