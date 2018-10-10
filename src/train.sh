#!/bin/bash

source ../config/default_config.sh #always load default settings from config file here
source $1 #first command line argument is the config file with specific settings -- it overrides settings in default_config.sh if added

src_vocab=$MAIN_FOLDER$VOCAB$VOCAB_NAME$ext_src
tgt_vocab=$MAIN_FOLDER$VOCAB$VOCAB_NAME$ext_tgt

## First get word embeddings for this vocab - if we added "word" as second argument ###
if [[ $representation = "word" || $representation = 'char_word' ]]; then
	src_embed=$MAIN_FOLDER$embed$src_id$emb_ext
	tgt_embed=$MAIN_FOLDER$embed$tgt_id$emb_ext

	if [[ ! -f $src_embed ]] && [[ ! -f $tgt_embed ]]; then #only create if not exists already
		mkdir -p $MAIN_FOLDER$embed
		th $EMBED_LUA -embed_type $embed_type -embed_file $embed_file -save_data $MAIN_FOLDER$embed$src_id -dict_file $src_vocab
		th $EMBED_LUA -embed_type $embed_type -embed_file $embed_file -save_data $MAIN_FOLDER$embed$tgt_id -dict_file $tgt_vocab
	else
		echo "Embed file already exists, skip creating $src_embed and $tgt_embed"
	fi

	# Overwrite (possible) values of config file
	pre_word_vecs_enc="-pre_word_vecs_enc $src_embed"
	pre_word_vecs_dec="-pre_word_vecs_dec $tgt_embed"	
fi

# Set variables
train_src=$MAIN_FOLDER$WORKING$TRAIN$gold_train$sent_ext$char_sent_ext
train_tgt=$MAIN_FOLDER$WORKING$TRAIN$gold_train$char_drs_ext
valid_src=$MAIN_FOLDER$WORKING$DEV$gold_dev$sent_ext$char_sent_ext
valid_tgt=$MAIN_FOLDER$WORKING$DEV$gold_dev$char_drs_ext
START=1

### Training over (possibly) multiple runs ###
for run in $(eval echo "{$START..$num_runs}")
do
	# First create extra directory for the models if num_runs > 1
	if [[ (( $num_runs -gt 1)) ]]; then
		mod_folder="model_$run"
		mkdir -p $MAIN_FOLDER$MODELS$mod_folder
	else
		mod_folder=""
	fi
	
	model_folder="$MAIN_FOLDER$MODELS${mod_folder}/"
	random_seed=$RANDOM #use a different random seed every time, but can also fix a seed here
	echo "Start training run ${run}/$num_runs"
	th $TRAIN_LUA -train_src $train_src -train_tgt $train_tgt -valid_src $valid_src -valid_tgt $valid_tgt -src_vocab $src_vocab -tgt_vocab $tgt_vocab -src_seq_length $src_seq_length -tgt_seq_length $tgt_seq_length -src_word_vec_size $src_word_vec_size -tgt_word_vec_size $tgt_word_vec_size -layers $layers -rnn_size $rnn_size -rnn_type $rnn_type -save_model "$MAIN_FOLDER$MODELS${mod_folder}/model" -log_file $MAIN_FOLDER$LOG$log_file_train -dropout $dropout $dropout_input -dropout_words $dropout_words -dropout_type $dropout_type $residual -bridge $bridge -encoder_type $encoder_type -attention $attention -max_pos $max_pos -global_attention $global_attention -report_every $report_every -end_epoch $end_epoch -validation_metric $validation_metric -max_batch_size $max_batch_size -optim $optim -learning_rate $learning_rate -max_grad_norm $max_grad_norm -learning_rate_decay $learning_rate_decay -start_decay_at $start_decay_at $train_from $gpuid $pre_word_vecs_enc $pre_word_vecs_dec -seed $random_seed		
done
