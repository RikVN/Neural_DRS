#!/bin/bash
set -eu -o pipefail

# The files in the DRS_parsing repo only have gold, silver and bronze separately
# Combine them to files with gold + silver, gold + silver + bronze, etc
# There is no gold for non-English in 2.2.0, for 3.0.0 there is for German
for fol in data/2.2.0 data/3.0.0/ ; do
    for lang in en de it nl; do
        cd ${fol}/${lang}/
        # Silver + bronze (always)
        mkdir -p silver_bronze
        cat silver/train.txt bronze/train.txt > silver_bronze/train.txt
        cat silver/train.txt.raw bronze/train.txt.raw > silver_bronze/train.txt.raw
        # Do these combinations for English, or German 3.0.0
        if [[ $lang = "en" || ( $lang = "de" && $fol = "data/3.0.0/" ) ]] ; then
            # Gold + silver
            mkdir -p gold_silver
            cat gold/train.txt silver/train.txt > gold_silver/train.txt
            cat gold/train.txt.raw silver/train.txt.raw > gold_silver/train.txt.raw
            # Gold + silver + bronze
            mkdir -p gold_silver_bronze
            cat gold/train.txt silver/train.txt bronze/train.txt > gold_silver_bronze/train.txt
            cat gold/train.txt.raw silver/train.txt.raw bronze/train.txt.raw > gold_silver_bronze/train.txt.raw
        fi
        cd -
    done
done

# Add the tokenization files from Github to their correct folder
# And remove the now useless folder
mv data/*.txt.raw.tok.gold data/3.0.0/en/gold/
