#!/bin/bash

### Arguments: config-file input-file output-file model1 model2 model3 ...etc

source ../config/default_config.sh #always load default settings from config file here
source $1 #first command line argument is the config file with specific settings -- it overrides settings in default_config.sh if added


## NOTE: specifying multiple models can easily result in out-of-memory errors (on GPU)
## if you are parsing something that is not the small PMB data, be aware that this can happen

# Check if arguments are set -- $2 and $3 are input files and output files
if [ ! -z "$2" ] && [ ! -z "$3" ] && [ ! -z "$4" ]; then
	echo "Producing output..."
	echo "Input file: $2"
	echo "Output file: $3"
	# Get all models in a single param
	models="${@:4}"
	# Do parsing here
	th $TRANSLATE_LUA -src $2 -output $3 -model $models -beam_size $beam_size -max_sent_length $max_sent_length $replace_unk -n_best $n_best -length_norm $length_norm -coverage_norm $coverage_norm -eos_norm $eos_norm $gpuid
	# Postprocess
	python $POSTPROCESS_PY --input_file $3 --output_file $3$res_ext --var $var_rewrite --sig_file $sig_file
else
	echo "Usage: parse.sh CONFIG_FILE INPUT_FILE OUTPUT_FILE MODEL1 [MODEL2] [MODEL3] .."
fi	  
