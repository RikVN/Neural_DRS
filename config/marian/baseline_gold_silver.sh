#!/bin/bash
source config/marian/default_config.sh # get main folders from default settings

# Import to set every time, the folder in which we save all experiment results models, working files, output, logs, etc
MAIN_FOLDER="${GIT_HOME}/experiments/marian/baseline_gold_silver/"
# Gold files - if you do not plan on changing these after you set them,  you can also move them to default_config.sh
PRETRAINED_FOLDER="${GIT_HOME}/pmb_exp_data_3.0.0/en/gold_plus_silver/"
FINETUNED_FOLDER="${GIT_HOME}/pmb_exp_data_3.0.0/en/gold/"

# Important to set these for silver experiments
pretrained_train="train.txt"
pretrained_dev="dev.txt"
finetuned_train="train.txt"
finetuned_dev="dev.txt"

# Files that are used as input (sentences) are assumed to be in $file$sent_ext, i.e. dev.txt and dev.txt.raw
# Possibly overwrite default settings here:
sent_ext=".raw"
epochs_pre="6"
epochs_fine="6"
num_runs_fine=5
num_runs_pre=1
model_type="s2s"
fix=""

# For parsing from raw text this is already added in this config
# Note that this doesn't have to be in your config for your own
# experiments when retraining a model
VOCAB_FOR_PARSE="-v ${GIT_HOME}vocabs/marian/baseline_gold_silver/train.txt.raw.char.sent.yml ${GIT_HOME}vocabs/marian/baseline_gold_silver/train.txt.char.tgt.yml"
