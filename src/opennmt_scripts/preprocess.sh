#!/bin/bash
set -eu -o pipefail
# Preprocess script for the DRS parsing seq2seq experiments

source ../config/opennmt/default_config.sh #always load default settings from config file here
source $1 #first command line argument is the config file with specific settings -- it overrides settings in default_config.sh if added

# First create directories (if not there yet)
mkdir -p $MAIN_FOLDER
mkdir -p $MAIN_FOLDER$WORKING
mkdir -p $MAIN_FOLDER$WORKING$TRAIN
mkdir -p $MAIN_FOLDER$WORKING$DEV
mkdir -p $MAIN_FOLDER$MODELS
mkdir -p $MAIN_FOLDER$OUTPUT
mkdir -p $MAIN_FOLDER$OUTPUT$DEV
mkdir -p $MAIN_FOLDER$VOCAB
mkdir -p $MAIN_FOLDER$EVAL
mkdir -p $MAIN_FOLDER$LOG

# Copy the training files to the working directories (sentences and DRSs)
cp $GOLD_FOLDER$gold_train $MAIN_FOLDER$WORKING$TRAIN
cp $GOLD_FOLDER$gold_dev $MAIN_FOLDER$WORKING$DEV

cp $GOLD_FOLDER$gold_train$sent_ext $MAIN_FOLDER$WORKING$TRAIN
cp $GOLD_FOLDER$gold_dev$sent_ext $MAIN_FOLDER$WORKING$DEV

# Do Python preprocessing to put files in character-level format, for train/dev
# Remove ill-formed DRSs from train set
python $PREPROCESS_PYTHON --input_file $MAIN_FOLDER$WORKING$TRAIN$gold_train --remove_ill --sig_file $sig_file --sentence_file $MAIN_FOLDER$WORKING$TRAIN$gold_train$sent_ext --casing $casing --representation $representation --variables $var_rewrite --char_drs_ext $char_drs_ext --char_sent_ext $char_sent_ext --var_drs_ext $var_drs_ext
python $PREPROCESS_PYTHON --input_file $MAIN_FOLDER$WORKING$DEV$gold_dev --sentence_file $MAIN_FOLDER$WORKING$DEV$gold_dev$sent_ext --casing $casing --representation $representation --variables $var_rewrite --char_drs_ext $char_drs_ext --char_sent_ext $char_sent_ext --var_drs_ext $var_drs_ext

# Then do OpenNMT preprocessing to create the vocabulary files
train_src=$MAIN_FOLDER$WORKING$TRAIN$gold_train$sent_ext$char_sent_ext
train_tgt=$MAIN_FOLDER$WORKING$TRAIN$gold_train$char_drs_ext
valid_src=$MAIN_FOLDER$WORKING$DEV$gold_dev$sent_ext$char_sent_ext
valid_tgt=$MAIN_FOLDER$WORKING$DEV$gold_dev$char_drs_ext
log_file=$MAIN_FOLDER$LOG$VOCAB_NAME$log_ext

th $PREPROCESS_LUA -train_src $train_src -train_tgt $train_tgt -valid_src $valid_src -valid_tgt $valid_tgt -save_data $MAIN_FOLDER$VOCAB$VOCAB_NAME -src_words_min_frequency $src_words_min_frequency -tgt_words_min_frequency $tgt_words_min_frequency -src_seq_length $src_seq_length -tgt_seq_length $tgt_seq_length -log_file $log_file
