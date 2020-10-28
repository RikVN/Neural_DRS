#!/bin/bash
set -eu -o pipefail

# Get the DRS parsing repo with the scripts (Counter) and data
git clone https://github.com/RikVN/DRS_parsing
cd DRS_parsing

pip install -r requirements.txt
pip install scipy
pip install matplotlib
cd ../

# Create data folder, download files and unzip
# Get the data
cd data/
wget "https://pmb.let.rug.nl/releases/exp_data_2.2.0.zip"
wget "https://pmb.let.rug.nl/releases/exp_data_3.0.0.zip"
## Unzip and rename
unzip exp_data_2.2.0.zip
unzip exp_data_3.0.0.zip
mv exp_data_2.2.0 2.2.0
mv pmb_exp_data_3.0.0 3.0.0
# Clean up zips
rm exp_data_2.2.0.zip
rm exp_data_3.0.0.zip
cd ../

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
