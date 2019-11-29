#!/bin/bash
source config/marian/default_config.sh # get main folders from default settings

# Import to set every time, the folder in which we save all experiment results models, working files, output, logs, etc
MAIN_FOLDER="${GIT_HOME}/experiments/marian/best_gold_only/"
# Gold files - if you do not plan on changing these after you set them,  you can also move them to default_config.sh
PRETRAINED_FOLDER="${EVAL_GIT_HOME}/data/pmb-2.2.0/gold/"
FINETUNED_FOLDER=""

# Important to set these for silver experiments
pretrained_train="train.txt"
pretrained_dev="dev.txt"
finetuned_train="train.txt"
finetuned_dev="dev.txt"

# Files that are used as input (sentences) are assumed to be in $file$sent_ext, i.e. dev.txt and dev.txt.raw
# Possibly overwrite default settings here:
sent_ext=".raw"
epochs_pre="13"
epochs_fine="6"
num_runs_fine=5
num_runs_pre=1
# Set multi-src extension to add
multi_src_ext=".lemsemposccgdep"
model_type="multi-s2s"

# For parsing from raw text this is already added in this config
# Note that this doesn't have to be in your config for your own
# experiments when retraining a model
VOCAB_FOR_PARSE="-v ${GIT_HOME}vocabs/marian/best_gold_only/train.txt.raw.char.sent.yml ${GIT_HOME}vocabs/marian/best_gold_only/train.txt.lemsemposccgdep.yml ${GIT_HOME}vocabs/marian/best_gold_only/train.txt.char.tgt.yml"
