#!/bin/bash
# Preprocess script for the DRS parsing seq2seq experiments
# Creates directory setup for the experiment and preprocess the files based on
# certain parameter settings (usually character-level input)
# Arguments :
# 		 $1 : config file with settings for the experiments

source config/marian/default_config.sh #always load default settings from config file here
source $1 #first command line argument is the config file with specific settings -- it overrides settings in default_config.sh if added

setup_dirs(){
	# Setup all directories of the experiment
	for subdir in $WORKING $MODELS $OUTPUT $EVAL $LOG; do
		mkdir -p $MAIN_FOLDER$subdir
		for type in $PRETRAINED $FINETUNED; do
			mkdir -p $MAIN_FOLDER$subdir$type
			# Add train/dev in the working folder
			if [[ $subdir == $WORKING ]] ; then
				for data in $TRAIN $DEV; do
					mkdir -p $MAIN_FOLDER$subdir$type$data
				done
			fi
		done
	done
}

copy_configs(){
	# Create a backup of the config files in the experiment folder (reproducibility)
	# Mainly because so we can change the default, but still know what we used here
	mkdir -p "${MAIN_FOLDER}config/"
	cp config/marian/default_config.sh "${MAIN_FOLDER}config/"
	cp $1 "${MAIN_FOLDER}config/"
}

copy_finetune_files(){
	cp $FINETUNED_FOLDER$finetuned_train $MAIN_FOLDER$WORKING$FINETUNED$TRAIN
	cp $FINETUNED_FOLDER$finetuned_dev $MAIN_FOLDER$WORKING$FINETUNED$DEV
	cp $FINETUNED_FOLDER$finetuned_train$sent_ext $MAIN_FOLDER$WORKING$FINETUNED$TRAIN
	cp $FINETUNED_FOLDER$finetuned_dev$sent_ext $MAIN_FOLDER$WORKING$FINETUNED$DEV
}


copy_initial_files(){
	cp $PRETRAINED_FOLDER$pretrained_train $MAIN_FOLDER$WORKING$PRETRAINED$TRAIN
	cp $PRETRAINED_FOLDER$pretrained_dev $MAIN_FOLDER$WORKING$PRETRAINED$DEV
	cp $PRETRAINED_FOLDER$pretrained_train$sent_ext $MAIN_FOLDER$WORKING$PRETRAINED$TRAIN
	cp $PRETRAINED_FOLDER$pretrained_dev$sent_ext $MAIN_FOLDER$WORKING$PRETRAINED$DEV
}


copy_multi_src_files(){
	for cp_ext in $multi_src_ext; do
		cp $PRETRAINED_FOLDER$pretrained_train$cp_ext $MAIN_FOLDER$WORKING$PRETRAINED$TRAIN
		cp $PRETRAINED_FOLDER$pretrained_dev$cp_ext $MAIN_FOLDER$WORKING$PRETRAINED$DEV
		if [[ -n "$FINETUNED_FOLDER" ]]; then
			cp $FINETUNED_FOLDER$finetuned_train$cp_ext $MAIN_FOLDER$WORKING$FINETUNED$TRAIN
			cp $FINETUNED_FOLDER$finetuned_dev$cp_ext $MAIN_FOLDER$WORKING$FINETUNED$DEV
		fi
	done
}

preprocess_drs(){
	# Preprocess DRS files
	# $1 is the DRS file, $2 the sentence file
	python $PREPROCESS_PYTHON --input_file $1 --sentence_file $2 --casing $casing --representation $representation --variables $var_rewrite --char_drs_ext $char_tgt_ext --char_sent_ext $char_sent_ext --var_drs_ext $var_drs_ext $shift_chars $no_sents $same_box
}

#### MAIN ####

# Setup all directories
setup_dirs
# Backup config files for reproducibility
copy_configs $1

# We either do training, or first pretraining and then finetuning
# Copy the files for pretraining to experiment folder
echo "Copying files..."
copy_initial_files

# If we also do fine-tuning, copy those as well
if [[ -n "$FINETUNED_FOLDER" ]]; then
	copy_finetune_files
fi

# If we do multi-src encoding, we have to copy all the files with the extensions there as well
if [[ -n "$multi_src_ext" ]]; then
	echo "Adding multi-src files..."
	copy_multi_src_files
fi

echo "Preprocessing pretrain files..."
# Do Python preprocessing to put files in character-level format, for train/dev for silver and gold
preprocess_drs $MAIN_FOLDER$WORKING$PRETRAINED$TRAIN$pretrained_train $MAIN_FOLDER$WORKING$PRETRAINED$TRAIN$pretrained_train$sent_ext
preprocess_drs $MAIN_FOLDER$WORKING$PRETRAINED$DEV$pretrained_dev $MAIN_FOLDER$WORKING$PRETRAINED$DEV$pretrained_dev$sent_ext
if [[ -n "$FINETUNED_FOLDER" ]]; then
	echo "Preprocessing initial files..."
	preprocess_drs $MAIN_FOLDER$WORKING$FINETUNED$TRAIN$finetuned_train $MAIN_FOLDER$WORKING$FINETUNED$TRAIN$finetuned_train$sent_ext
	preprocess_drs $MAIN_FOLDER$WORKING$FINETUNED$DEV$finetuned_dev $MAIN_FOLDER$WORKING$FINETUNED$DEV$finetuned_dev$sent_ext
fi
