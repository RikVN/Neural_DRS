#!/bin/bash
source config/marian/default_config.sh # get main folders from default settings

# Import to set every time, the folder in which we save all experiment results models, working files, output, logs, etc
MAIN_FOLDER="${GIT_HOME}/experiments/marian/sample/"
# Gold files - if you do not plan on changing these after you set them,  you can also move them to default_config.sh
PRETRAINED_FOLDER="${EVAL_GIT_HOME}/data/pmb-3.0.0/sample/"
FINETUNED_FOLDER="${EVAL_GIT_HOME}/data/pmb-3.0.0/sample/"

# Important to set these for silver experiments
pretrained_train="train.txt"
pretrained_dev="dev.txt"
finetuned_train="train.txt"
finetuned_dev="dev.txt"

# Files that are used as input (sentences) are assumed to be in $file$sent_ext, i.e. dev.txt and dev.txt.raw
# Possibly overwrite default settings here:
sent_ext=".raw"
epochs_pre="3"
epochs_fine="3"
num_runs_fine=3
num_runs_pre=1
