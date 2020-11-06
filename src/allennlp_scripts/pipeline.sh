#!/bin/bash

# Run AllenNLP experiments
    # $1 is a JSON config file
    # $2 is the folder we save our experiment
    # $3 type of experiment: "fine" does finetuning anything else just does normal training (have to add something)
    # $4 is the language we do DRS parsing for, needed to get the gold standard dev/test files. Has to be en/de/it/nl
    # All arguments need to be there or the script will error

set -eu -o pipefail

# Load settings etc from settings.sh
source src/allennlp_scripts/settings.sh

# Export paths to be sure
export PYTHONPATH=${DRS_GIT}/evaluation/:${PYTHONPATH}
export PYTHONPATH=${NEURAL_GIT}/src/:${PYTHONPATH}

# For experiments etc, see MAIN below. First the functions are listed

############################ FUNCTIONS #############################

# Set all important folders etc
setup(){
    config_file=$1
    exp_dir=$2
    exp_type=$3
    lang=$4

    # If we are fine-tuning, save in fine-tuned and set model
    if [[ $3 = 'fine'* ]]; then
        pretrain_model="${exp_dir}/run1/models/model.tar.gz"
        exp_dir="${exp_dir}run1/fine-tuned/"
    fi
    mkdir -p $exp_dir

    # Get variables from config folder (hacky method but works, surely could be done differently but oh well)
    EPOCHS=$(cat $config_file | sed -e 's/,/\n/g' | grep 'num_epochs"' | grep -oP "\d+")
    train=$(cat $config_file | sed -e 's/,/\n/g' | grep '"train_data_path"' | awk '{$1=$1;print}' | cut -d ' ' -f2 | sed -e 's/"//g')
    dev=$(cat $config_file | sed -e 's/,/\n/g' | grep '"validation_data_path"' | awk '{$1=$1;print}' | cut -d ' ' -f2 | sed -e 's/"//g')
    test=$(cat $config_file | sed -e 's/,/\n/g' | grep '"test_data_path"' | awk '{$1=$1;print}' | cut -d ' ' -f2 | sed -e 's/"//g') || true

    # Gold dev/test we know because of the language
    gold_dev="${NEURAL_GIT}/data/3.0.0/${lang}/gold/dev.txt"
    gold_test="${NEURAL_GIT}/data/3.0.0/${lang}/gold/test.txt"

    # Print this to make sure all went well
    print_info
}

# Print current information of experiment so we can check all went well
print_info(){
    echo "Exp overview:"
    echo "Language: $lang"
    echo "Exp dir: $exp_dir"
    echo "Train: $train"
    echo "Dev: $dev"
    echo "Gold dev: $gold_dev"
    echo "Gold test: $gold_test"
    echo ""
}

# get all the feature files for dev/test that we add as argument for predict (maybe)
# $1: config file
# $2: validation/test, so that we find the correct files
get_feat_files(){
    feat_string=""
    # Loop over the features we possibly add
    for feat in sem ccg lem dep pos char; do
        # Set the string that we will grep for in the config file (e.g. validation_data_path_sem)
        grep_str="${2}_data_path_${feat}"
        # Grep for the file, if it doesn't exist the string is empty, so we can add it to feat_string anyway
        feat_file=$(cat $1 | sed -e 's/,/\n/g' | grep $grep_str | awk '{$1=$1;print}' | cut -d ' ' -f2 | sed -e 's/"//g') || true
        feat_string="$feat_string $feat_file"
    done

    # Only if we found a file we add --feature-files to the string
    if [[ -z "${feat_string// }" ]] ; then
        feat_string=""
        echo "Not adding feature files for predicting"
    else
        feat_string="--feature-files $feat_string"
        echo "Adding feature files for predicting:"
        echo $feat_string
        echo
    fi
}


# Set folders now to avoid allenNLP non-empty error
create_folders(){
    for subfol in log output eval metrics config models; do
        mkdir -p ${1}/${subfol}/
    done
}


# $1 is current directory and $2 is the out file, $3 the epoch number suffix (empty can be fine as well)
# $4 is dev/test indicator for log files
# $5 is the gold dev/test set
pp_and_counter(){
    # Only postprocess if file exists
    if [ -f "$2" ]; then
        if [[ ! -f "${2}.out" || $FORCE_PP = true ]]; then
            # Find the vocabulary, if target.txt exists take that, else tokens.txt
            if [[ -f "${1}/vocabulary/target.txt" ]]; then
                vocab_file="${1}/vocabulary/target.txt"
            else
                vocab_file="${1}/vocabulary/tokens.txt"
            fi
            python $PP_PY --input_file $2 --output_file ${2}.out --sig_file $SIG_FILE --fix --json --sep $SEP -rcl $REMOVE_CLAUSES -m $MIN_TOKENS -voc $vocab_file $no_sep > ${1}log/$4_pp$3.log

            # Run Counter evaluation
            python $COUNTER -f1 ${2}.out -f2 $5 -g $SIG_FILE -prin > ${1}eval/$4_eval$3.txt
        else
            echo "Already did postprocessing, skip ${2}.out"
        fi
    else
        echo "Output file $2 doesn't exist, skip pp + counter"
    fi
}

# Train AllenNLP model, do fine-tuning depending on the current settings
# $1: input argument for cmd line $2, whether we finetune or not
# $2: current directory ($cur_dir)
train(){
    echo "Training + predicting run $run"
    if [[ $1 = "fine" || $1 = "finetune"  || $1 = "finetuning" ]]; then
        echo "Finetuning model from $pretrain_model"
        allennlp fine-tune -m $pretrain_model -c $config_file -s $2
    else
        echo "Training model from scratch, not finetuning"
        allennlp train $config_file -s $2 $FORCE
    fi
}

# Do tarring for our ourselves because we always want to take the last one, not lowest loss
tar_model(){
    # Move model to place we will copy from
    mv $model_state ${cur_dir}/weights.th
    # Sleep a bit to make sure copying is finished, probably not needed but anyway
    sleep 3
    # Do tarring here
    cd $cur_dir ; tar -zcvf $model_file $VOCAB $CONFIG weights.th ; cd -
    # If tarring succeeded remove all unnecessary model files to save space
    if [[ -f $cur_dir$model_file ]]; then
        echo "Removing all model files to save space..."
        rm ${cur_dir}/*th
    fi
}

# Do some cleaning in the experiment folder and backup the script files for reproduction
# $1: experiment folder
cleanup(){
    mv ${1}*.log ${1}/log/ || true
    mv ${1}metrics*json ${1}/metrics/ || true
    cp ${1}config.json ${1}config/ || true
    mv ${1}model.tar.gz ${1}models/ || true
}


############################ MAIN #############################

# Setup
setup $1 $2 $3 $4

# Set predefined random seeds for reproducibility
seeds=(2222 3333 4444 5555 6666)
START=1

# Number of runs depends on whether we're finetuning or not
if [[ $3 = "fine" || $3 = "finetune"  || $3 = "finetuning" ]]; then
    END=5
else
    END=1
fi

# Set start run and print to screen
echo "Start run $START, end run $END"
let "idx = $START + 1 - 2" || true


# Loop over the runs for the training
for run in $(eval echo "{$START..$END}"); do
    echo "Currently at run $run/$END"

    # Select and set random seed, JSON configs knows about exported variables
    CUR_SEED=${seeds[$idx]}
    export CUR_SEED=$CUR_SEED
    echo "Set random seed to $CUR_SEED"
    let "idx=$idx+1"

    # Create directory for current run
    cur_dir="${exp_dir}run$run/"
    mkdir -p $cur_dir

    # Set out file for dev/test
    out_file="${cur_dir}output/output_dev_epoch_${EPOCHS}.seq.drs"
    out_file_test="${cur_dir}output/output_test_epoch_${EPOCHS}.seq.drs"

    # Do the training here
    # If we are fine-tuning things are a bit different than normal training
    echo "Train for $EPOCHS epochs"
    train $3 $cur_dir

    # Then create folders to avoid errors
    create_folders $cur_dir

    # Now do the testing/predicting with the trained model
    # Have to do -1 because index of allennlp models starts at 0
    echo "Predicting output for single model..."
    let "num_epochs = $EPOCHS - 1" || true

    # We always take the last trained model, not the one with lowest validation loss
    model_state="${cur_dir}model_state_epoch_${num_epochs}.th"
    if [[ -f $model_state ]]; then
        # We have to create our own .tar.gz model to do the prediction in that case
        tar_model
        # First check if we have to add feature_files
        get_feat_files $config_file "validation"
        # Then finally do the predicting on the dev set
        allennlp predict ${cur_dir}model.tar.gz $dev --use-dataset-reader --cuda-device 0 --predictor seq2seq --output-file $out_file $SILENT $feat_string
        # After predicting we postprocess and evaluate
        pp_and_counter $cur_dir $out_file "" "dev" $gold_dev
        # Same procedure for test, if we specified the file in the config
        if [[ ! -z $test ]]; then
            get_feat_files $config_file "test"
            allennlp predict ${cur_dir}model.tar.gz $test --use-dataset-reader --cuda-device 0 --predictor seq2seq --output-file $out_file_test $SILENT $feat_string
            pp_and_counter $cur_dir $out_file_test "" "test" $gold_test
        fi
    else
        echo "No model state $model_state, can't do prediction..."
    fi

    # Cleanup folders
    cleanup $cur_dir
done
