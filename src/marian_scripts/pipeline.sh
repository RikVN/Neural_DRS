#!/bin/bash
set -eu -o pipefail

# Do a pipeline of preprocessing, training, parsing and evaluating for Marian models

# Always load default settings from config file here
source config/marian/default_config.sh
# First command line argument is the config file with specific settings -- it overrides settings in default_config.sh if added
source $1

preprocess(){
	# Preprocessing if files do not exist yet
	if [[ ! -f $MAIN_FOLDER$WORKING$PRETRAINED$TRAIN$pretrained_train$char_tgt_ext ]]; then
		$PREPROCESS_SH $1
	fi
}

set_vocabs(){
	# Set the vocabs correctly
	# For multi-src encoding we have an extra vocab
	extra_vocab_src=""
	if [[ -n "$multi_src_ext" ]]; then
		for mul_ext in $multi_src_ext; do
			extra_vocab_src="$extra_vocab_src $MAIN_FOLDER$WORKING$PRETRAINED$TRAIN$pretrained_train${mul_ext}.yml"
		done
	fi

	# Then set the vocab
	vocab_src="$MAIN_FOLDER$WORKING$PRETRAINED$TRAIN$pretrained_train$sent_ext${char_sent_ext}.yml"
	vocab_tgt="$MAIN_FOLDER$WORKING$PRETRAINED$TRAIN$pretrained_train${char_tgt_ext}.yml"
	extra_vocab="-v $vocab_src $extra_vocab_src $vocab_tgt"
}

copy_vocabs(){
	# Copy vocabulary from pretrained to finetuned folder (just to be sure)
	for in_file in "$MAIN_FOLDER$WORKING$PRETRAINED$TRAIN"*".yml"; do
		filename=$(basename -- "$in_file")
		cp $in_file "$MAIN_FOLDER$WORKING$FINETUNED$TRAIN$filename"
	done
}

set_dataset_vars(){
	# Set variables -- check if we do multi-source training, then add more src files for train/dev
	# $1 is the identifier, i.e. pretrained or finetuned
	# $2 gold train file name
	# $3 gold dev file name
	train_src="$MAIN_FOLDER$WORKING$1$TRAIN$2$sent_ext$char_sent_ext"
	valid_src="$MAIN_FOLDER$WORKING$1${DEV}$3$sent_ext$char_sent_ext"

	if [[ -n "$multi_src_ext" ]]; then
		echo "Doing multi-source training"
		# Loop over extensions to add the files
		for mul_ext in $multi_src_ext; do
			train_src="$train_src $MAIN_FOLDER$WORKING$1$TRAIN$2$mul_ext"
			valid_src="$valid_src $MAIN_FOLDER$WORKING$1${DEV}$3$mul_ext"
		done
	else
		echo "Doing single-source training"
	fi
	train_tgt=$MAIN_FOLDER$WORKING$1$TRAIN$2$char_tgt_ext
	valid_tgt=$MAIN_FOLDER$WORKING$1$DEV$3$char_tgt_ext
}

write_average(){
	# Write averages to a file to easier check the results when doing multiple runs
	# Arguments: $1 num runs, $2 folder with eval files
	if [[ (( $1 -gt 1)) ]]; then
		python $AVERAGE_PY -f $2
	fi
}

train() {
	# Train a model, this function has the following arguments
	# $1 is the identifier - pretrain or finetune
	# $2 is the config file
	# $3 is the number of runs
	# $4 is the number of epochs
	# $5 name of gold train
	# $6 name of gold dev

	# Load all train/dev sets in variables (train/dev_src/tgt)
	set_dataset_vars $1 $5 $6
	# Set predefined random seeds if not present in config file
	if [[ -z ${seeds+x} ]]; then
		seeds=(4321 1111 2222 3333 4444 5555 6666 7777 8888 9999)
	fi
	let idx=0 || true # to not end the script https://unix.stackexchange.com/questions/63166/bash-e-exits-when-let-or-expr-evaluates-to-0

	# Loop over multiple runs
	for run in $(eval echo "{$START..$3}")
	do
		model_file="$MAIN_FOLDER$MODELS${1}model${run}.npz"
		log_train="$MAIN_FOLDER$LOG${1}train${run}.log"
		log_translate="$MAIN_FOLDER$LOG${1}translate${run}.log"
		log_valid="$MAIN_FOLDER$LOG${1}valid${run}.log"
		# Only do if we didn't do this before - automatically skip runs this way
		if [[ ! -f $model_file ]]; then
			# Select random seed
			let "idx=$idx+1"
			random_seed=${seeds[$idx]}
			echo "Start training run $run"

			# Do training here
			${MARIAN_HOME}marian -t $train_src $train_tgt --valid-sets $valid_src $valid_tgt --valid-freq $valid_freq $vocab -w $workspace --log $log_train --log-level $log_level --seed $random_seed $pretrain --type $model_type --dim-vocabs $dim_vocabs --dim-emb $dim_emb --dim-rnn $dim_rnn --enc-type $enc_type --enc-cell $enc_cell --enc-depth $enc_depth --dec-cell $dec_cell --dec-depth $dec_depth $skip $layer_normalization $best_deep $right_left --dropout-rnn $dropout_rnn --max-length $max_length $max_length_crop -e $4 --disp-freq $disp_freq --save-freq $save_freq -d $gpuid --mini-batch $mini_batch -o $optimizer -l $learning_rate --lr-decay $lr_decay --lr-decay-strategy $lr_decay_strategy --lr-decay-start $lr_decay_start --clip-norm $clip_norm --valid-metrics $valid_metric --valid-mini-batch $mini_batch --valid-max-length $max_length --valid-log $log_valid -b $beam_size -n $norm --max-length-factor $max_length_factor $allow_unk $n_best --cost-type $cost_type -m $model_file $embedding --dropout-src $dropout_src --dropout-trg $dropout_tgt --label-smoothing $label_smoothing $extra_vocab

			# Do the translation of the dev set here
			output_file="$MAIN_FOLDER$OUTPUT$1output$run$output_ext"
			${MARIAN_HOME}marian-decoder $extra_vocab -w $workspace --log $log_translate --log-level $log_level --seed $random_seed -m $model_file --type $model_type -i $valid_src -b $beam_size -n $norm $allow_unk $n_best --max-length $max_length --max-length-factor $max_length_factor -d $gpuid --mini-batch $mini_batch > $output_file

			# Do postprocessing of the output file
			# Do it twice, with and without referee
			log_pp="$MAIN_FOLDER$LOG${1}postprocess$run.log"
			log_noref="$MAIN_FOLDER$LOG${1}postprocess_no_ref$run.log"
			python $POSTPROCESS_PY -i ${output_file} -o ${output_file}.res -v $var_rewrite -s $sig_file -rcl $remove_clauses -se $sep $fix  > $log_pp
			python $POSTPROCESS_PY -i ${output_file} -o ${output_file}.noref -v $var_rewrite -s $sig_file --no_referee -rcl $remove_clauses -se $sep > $log_noref

			# Then do evaluation with Counter, also twice (get individual file)
			eval_file="$MAIN_FOLDER$EVAL${1}eval$run.txt"
			idv_file="$MAIN_FOLDER$EVAL${1}idv$run.txt"
			gold_valid="$MAIN_FOLDER$WORKING$1${DEV}$6"
			python $COUNTER -f1 ${output_file}.res -f2 $gold_valid -prin -r 25 --signature $sig_file $ill > $eval_file
			python $COUNTER -f1 ${output_file}.res -f2 $gold_valid -prin -r 25 --signature $sig_file -ms -ms_file $idv_file $ill
		else
			echo "Skip run $run, model file already exists"
		fi
	done
	# Write average scores to file if we did more than 1 run
	write_average $3 $MAIN_FOLDER$EVAL$1
}

##### Main pipeline #####

# Don't import referee from other locations (only for PMB people, I guess)
export PYTHONPATH=${EVAL_GIT_HOME}evaluation/:${PYTHONPATH}

# Preprocess all data
preprocess $1
# Set vocabs, they are the same for pre/fine
set_vocabs

# Always do (pre)training, only do finetuning if we want that
echo "Doing initial training..."
train $PRETRAINED $1 $num_runs_pre $epochs_pre $pretrained_train $pretrained_dev

# Now do fine-tuning if we want
if [[ -n "$FINETUNED_FOLDER" ]]; then
	# First set pretrained model to last one we trained previously
	pretrain="--pretrained-model $model_file"

	# Copy the previous vocabs (that we will use) to current folders as well
	copy_vocabs

	# Finally do the fine-tuning
	train $FINETUNED $1 $num_runs_fine $epochs_fine $finetuned_train $finetuned_dev
fi
