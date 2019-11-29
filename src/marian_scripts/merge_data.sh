#!/bin/bash
set -eu -o pipefail
DATA_FOLDER="/home/p266548/Documents/DRS_parsing/Neural_DRS/DRS_parsing/data/pmb-2.2.0/"

for data in train dev; do
	for type in gold gold_plus_silver; do
		python src/merge_tags.py --input_files ${DATA_FOLDER}${type}/${data}.txt.raw.lem ${DATA_FOLDER}${type}/${data}.txt.raw.sem ${DATA_FOLDER}${type}/${data}.txt.raw.pos ${DATA_FOLDER}${type}/${data}.txt.raw.ccg ${DATA_FOLDER}${type}/${data}.txt.raw.dep --char_exts .lem > ${DATA_FOLDER}${type}/${data}.txt.lemsemposccgdep
	done
done
