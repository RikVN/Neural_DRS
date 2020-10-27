#!/bin/bash
set -eu -o pipefail

# Get the DRS parsing repo with the scripts (Counter) and data
git clone https://github.com/RikVN/DRS_parsing
cd DRS_parsing

pip install -r requirements.txt
pip install scipy
pip install matplotlib
cd ../

# Get the 3.0.0 data
wget "https://pmb.let.rug.nl/releases/pmb_exp_data_3.0.0.zip"
# PMB website is down, temporarily get the files from here
#wget "http://www.let.rug.nl/rikvannoord/pmb_release/pmb_exp_data_3.0.0.zip"
unzip pmb_exp_data_3.0.0.zip

# The files in the DRS_parsing repo only have gold and silver separately
# Combine them to files with gold + silver to reproduce experiments
# You can use similar scripts to do gold + bronze, gold + silver + bronze, etc
for fol in DRS_parsing/data/pmb-2.1.0 DRS_parsing/data/pmb-2.2.0 pmb_exp_data_3.0.0/en/ ; do
	cd $fol
	mkdir -p gold_plus_silver
	cat gold/train.txt silver/train.txt > gold_plus_silver/train.txt
	cat gold/train.txt.raw silver/train.txt.raw > gold_plus_silver/train.txt.raw
	# Also put the dev and test files there, but they are just gold
	cp gold/dev.txt gold_plus_silver/dev.txt
	cp gold/dev.txt.raw gold_plus_silver/dev.txt.raw
	cp gold/test.txt gold_plus_silver/test.txt
	cp gold/test.txt.raw gold_plus_silver/test.txt.raw
	cd -
done
