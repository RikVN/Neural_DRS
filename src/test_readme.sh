#!/bin/bash
set -eu -o pipefail

# Run all the examples that are in the README to check that they still work
# Should be very similar to unit_tests.sh

printf "\n----------------------------------------------\n"
printf "Testing all examples of the README\n"
printf "You have to have run ./setup.sh first\n"
printf "Make sure you added the right main folder in config/opennmt/default_config.sh and config/marian/default_config.sh\n"
printf "If not, this script will fail\n\n"

cur_dir=$(pwd)
SENT_FILE="${cur_dir}/DRS_parsing/data/pmb-3.0.0/sample/train.txt.raw"
INPUT_FILE=${SENT_FILE}.char.sent
OUTPUT_FILE=${SENT_FILE}.seq.drs
MODEL1="${cur_dir}/models/opennmt/best_gold_silver.npz"

#### OpenNMT experiments

## Preprocessing
python src/preprocess.py -s $SENT_FILE -c feature -r char --sents_only

## Parsing with OpenNMT from raw text
cd OpenNMT
../src/opennmt_scripts/parse.sh ../config/opennmt/parse_best_config.sh $INPUT_FILE $OUTPUT_FILE $MODEL1

## Preprocessing and training
../src/opennmt_scripts/preprocess.sh ../config/opennmt/sample.sh
../src/opennmt_scripts/train.sh ../config/opennmt/sample.sh
## Parse with new model
MODEL1=$(ls ${cur_dir}/experiments/opennmt/sample/models/model_epoch3*t7)
../src/opennmt_scripts/parse.sh ../config/opennmt/sample.sh $INPUT_FILE $OUTPUT_FILE $MODEL1
cd ../

# Since there is no gold output for sample, just test Counter here with gold data we know of
GOLD_DEV="${cur_dir}/DRS_parsing/data/pmb-3.0.0/gold/dev.txt"
SIG_FILE="${cur_dir}/DRS_parsing/evaluation/clf_signature.yaml"
python DRS_parsing/evaluation/counter.py -f1 $GOLD_DEV -f2 $GOLD_DEV -g $SIG_FILE

#### Marian experiments

# Extract linguistic features with Marian

./src/marian_scripts/extract_ling_features.sh $SENT_FILE
python src/merge_tags.py -f ${SENT_FILE}.pos ${SENT_FILE}.dep ${SENT_FILE}.ccg ${SENT_FILE}.lem --char_exts .lem > ${SENT_FILE}.multi
python src/merge_tags.py -f ${SENT_FILE}.lem --char_exts .lem > ${SENT_FILE}.clem

# Now parse using the best Marian model
PRETRAINED_MODEL="${cur_dir}/models/marian/best_gold_silver.npz"
OUTPUT_FILE="${SENT_FILE}.seq.marian"
./src/marian_scripts/parse_raw_text.sh config/marian/best_gold_silver.sh $PRETRAINED_MODEL $OUTPUT_FILE $SENT_FILE ${SENT_FILE}.clem

# Train new Marian model, use sample data instead of gold + silver from README (takes too long)
./src/marian_scripts/pipeline.sh config/marian/sample.sh
