#!/bin/bash
set -Exeuo pipefail

# pre-processing
for type in train dev test; do
  python src/preprocess.py --input_file DRS_parsing/data/pmb-3.0.0/gold/${type}.txt -v rel -r word -cd .tgt --drss_only;
done

for type in train dev test; do
  python src/preprocess.py --sentence_file DRS_parsing/data/pmb-3.0.0/gold/${type}.txt.raw -r char -cs .char.sent --sents_only -c feature;
done

for type in train dev test; do
  while IFS= read -r line1 && IFS= read -r line2 <&3; do
    echo -e "${line1}\t${line2}";
  done < DRS_parsing/data/pmb-3.0.0/gold/${type}.txt.raw.tok 3< DRS_parsing/data/pmb-3.0.0/gold/${type}.txt.tgt > DRS_parsing/data/pmb-3.0.0/gold/${type}.alp;
done

# train a small and simple BERT model
./src/allennlp_scripts/pipeline.sh config/allennlp/en/bert.json experiments/allennlp/en/bert/ normal en
# train a more complex model that uses characters, either in one or two encoders
./src/allennlp_scripts/pipeline.sh config/allennlp/en/bert_char_1enc.json experiments/allennlp/en/bert_char_1enc/ normal en
./src/allennlp_scripts/pipeline.sh config/allennlp/en/bert_char_2enc.json experiments/allennlp/en/bert_char_2enc/ normal en
# train a model that exploits semantic tags
./src/allennlp_scripts/pipeline.sh config/allennlp/en/bert_char_sem.json experiments/allennlp/en/bert_char_sem/ normal en
# fine-tune the bert_char_sem model on the gold data
./src/allennlp_scripts/pipeline.sh config/allennlp/en/bert_char_sem_fine.json experiments/allennlp/en/bert_char_sem/ fine en
