# AllenNLP experiments #

This document outlines how to run neural DRS parsing experiments using AllenNLP (and BERT). Details can be found in our [EMNLP paper](https://www.aclweb.org/anthology/2020.emnlp-main.371.pdf).

## Setting up ##

I used my own fork of AllenNLP 0.9.0. Throughout this README, I assume you followed the steps (setup.sh) in the main repository and that you are working from a Conda environment. Install AllenNLP as follows:

```
git clone https://github.com/RikVN/allennlp
cd allennlp
git checkout DRS
pip install --editable . ; cd ../
```

We also need to get the GloVe target embeddings (filtered for DRS parsing):

```
mkdir -p emb; cd emb
wget "http://www.let.rug.nl/rikvannoord/embeddings/glove_pmb.zip"
unzip glove_pmb.zip; rm glove_pmb.zip;  cd ../
```

If you only want to parse your raw texts with our best model, [skip ahead](#parsing-raw-text).

## Pre-processing ##

We now preprocess the sentences and DRSs to our preferred representation and in a format that AllenNLP can handle. For convenience we work with the data in DRS_parsing/data/pmb-3.0.0/, but we could of course use the larger data sets in data/.

Since we will use BERT at token-level (not full WordPiece), we want to use tokenized input sentences. This means we do not have to preprocess this tokenized file. Other settings are standard.

```
for type in train dev test; do python src/preprocess.py --input_file DRS_parsing/data/pmb-3.0.0/gold/${type}.txt -v rel -r word -cd .tgt --drss_only ; done
```

We want to add character-level information in two encoders, so we also preprocess the sentences to character-level:

```
for type in train dev test; do python src/preprocess.py --sentence_file DRS_parsing/data/pmb-3.0.0/gold/${type}.txt.raw -r char -cs .char.sent --sents_only -c feature ; done
```

AllenNLP expects the source and target side-by-side on a single line with a tab separating them:

```
for type in train dev test; do while IFS= read -r line1 && IFS= read -r line2 <&3; do   echo -e "${line1}\t${line2}"; done < DRS_parsing/data/pmb-3.0.0/gold/${type}.txt.raw.tok  3< DRS_parsing/data/pmb-3.0.0/gold/${type}.txt.tgt > DRS_parsing/data/pmb-3.0.0/gold/${type}.alp ; done
```

## Running small experiments ##

In AllenNLP, experiments are defined in config files, which are in JSON format. Examples for our best systems are in configs/allennlp/. We will only use them to quickly test our setup, so you have to adjust the training sets and number of epochs to actually run a full experiment. **Important:** make sure to change max_decoding_steps back to 1000 instead of 300 for running real experiments.

For training a model and predicting output I've added a pipeline script. As arguments it takes the config file, working experiment folder (will be created), whether we are training or fine-tuning and the language iso code we will be testing on (en/de/it/nl).

The pipeline script does the following things:

* Train a model based on the config file
* Use trained model to predict output for files specified config file
* Postprocess the predicted output, replace ill-formed with dummies
* Run [Counter](https://www.aclweb.org/anthology/L18-1267.pdf) to compare the postprocessed output with the gold standard

Let's see if we can train a small and simple BERT seq2seq model:

```
./src/allennlp_scripts/pipeline.sh config/allennlp/en/bert.json experiments/allennlp/en/bert/ normal en
```

Output, model and evaluation files are available in the experiment folder. We only trained for two epochs, so the results will not be great, of course.

You might get an error that says that there is no GPU available, even though you are using one. You might have to re-install pytorch for the correct CUDA version you are using (9.2 in my case). The numpy uninstall/install might not be necessary, but it was for me (see [here](https://stackoverflow.com/questions/54715835/numpy-is-installed-but-still-getting-error) as well). I don't really understand why the double install of pytorch is necessary, but otherwise I got errors:

```
conda install pytorch torchvision cudatoolkit=9.2 -c pytorch
conda install pytorch==1.3.1 torchvision cudatoolkit=9.2 -c pytorch
pip uninstall numpy
pip uninstall numpy
pip install numpy
```

You can also use a more complex model that uses characters, in either one or two encoders:

```
./src/allennlp_scripts/pipeline.sh config/allennlp/en/bert_char_1enc.json experiments/allennlp/en/bert_char_1enc/ normal en

./src/allennlp_scripts/pipeline.sh config/allennlp/en/bert_char_2enc.json experiments/allennlp/en/bert_char_2enc/ normal en
```

Finally, I've provided a config file that exploits [semantic tags](https://www.aclweb.org/anthology/W17-6901.pdf). This call works with the example data as I've added the output of a semantic tagger on the gold data to the DRS_parsing repo. However, for your own experiments you might want to tag sentences with a semantic tagger. An explanation on how to do this is available in [this README](Semtags.md).

```
./src/allennlp_scripts/pipeline.sh config/allennlp/en/bert_char_sem.json experiments/allennlp/en/bert_char_sem/ normal en
```

### Fine-tuning ###

In our experiments, we pre-train on gold + silver data and then fine-tune on only the gold data. The pipeline can take care of this. I assume you just trained the bert_char_sem model. As an example, we will now fine-tune on it for 1 epoch:

```
./src/allennlp_scripts/pipeline.sh config/allennlp/en/bert_char_sem_fine.json experiments/allennlp/en/bert_char_sem/ fine en
```

Note that I specified the bert_char_sem folder, not a new folder! You can find the fine-tuned results (automatically over 5 runs, not 1), in experiments/allennlp/en/bert_char_sem/run1/fine-tuned/.

## Languages other than English ##

It is also possible to train a model on non-English languages. I have added example configs for German experiments, training models for char-only, BERT-only, BERT + char (1enc) and BERT + char (2enc).

There are two differences between these and the English experiment. We use multi-lingual bert-base (uncased) and do not use semtags. The latter allows us to let the model handle the tokenization in a preprocessing step (spacy).

I assume you followed the setting up steps in the main repository and have the data files available in data/. First we preprocess the sets again and put them in AllenNLP format:

```
for type in train dev test; do python src/preprocess.py --input_file data/3.0.0/de/gold/${type}.txt -v rel -r word -cd .tgt --drss_only ; done

for type in train dev test; do python src/preprocess.py --input_file data/3.0.0/de/gold/${type}.txt  --sentence_file data/3.0.0/de/gold/${type}.txt.raw -r char -cs .char.sent -cd .char.tgt -v rel -c feature ; done

for type in train dev test; do while IFS= read -r line1 && IFS= read -r line2 <&3; do   echo -e "${line1}\t${line2}"; done < data/3.0.0/de/gold/${type}.txt.raw  3< data/3.0.0/de/gold/${type}.txt.tgt > data/3.0.0/de/gold/${type}.alp ; done

for type in train dev test; do while IFS= read -r line1 && IFS= read -r line2 <&3; do   echo -e "${line1}\t${line2}"; done < data/3.0.0/de/gold/${type}.txt.raw.char.sent  3< data/3.0.0/de/gold/${type}.txt.char.tgt > data/3.0.0/de/gold/${type}.char.alp ; done
```

Let's run the pipeline for a small example model:

```
./src/allennlp_scripts/pipeline.sh config/allennlp/de/bert.json experiments/allennlp/de/ normal de
```

And for the BERT + char in two encoder model:

```
./src/allennlp_scripts/pipeline.sh config/allennlp/de/bert_char_2enc.json experiments/allennlp/de/ normal de
```

You can run similar models for Italian and Dutch by adjusting the config files and doing the preprocessing as described above. Do not forget to change the tokenizer!

**Note**: if you run a character-level model, go to src/allennlp_scripts/settings.sh and change the values of no_sep and MIN_TOKENS as indicated.

## Testing your setup ##

You don't have to run all the individual commands above if you want to test if everything works (preprocessing, training, evaluation, etc), just run this:

```
./src/unit_tests_allennlp.sh
```

Running all the experiments can take over an hour, but you should get semi-decent output.

## Running your own experiments ##

You can adjust the config files to run your own experiments. Use the preprocessing scripts (see examples above) to put the data in the correct format. For DRS parsing, you probably want to use silver data as well, for example.

The added config files are examples. Please change the data files, number of epochs and max number of decoding steps in your own experiments! Specific configuration files from all our experiments as outlined in our paper are available upon request.

## Parsing raw text ##

The easiest way to parse raw text is using the model that uses BERT + characters in one encoder. First, download the model:

```
mkdir -p models/allennlp/
curl -o models/allennlp/bert_char_1enc.tar.gz http://www.let.rug.nl/rikvannoord/DRS/EMNLP/models/bert_char_1enc.tar.gz
```

Then just call the parsing script with the raw file, model and target vocab (available in vocabs/allennlp/). It will do post-processing and replace ill-formed DRSs by dummies, though you could change this by adding "--no_referee" to the $PP_PY call in the parse script.

```
./src/allennlp_scripts/parse.sh $SENT_FILE models/allennlp/bert_char_1enc.tar.gz vocabs/allennlp/tgt_bert_char_1enc.txt
```

The output file with DRSs is available in ${SENT_FILE}.drs.out.

Some notes: I limited the input to 50 tokens during training so the model also fits in 12GB GPU memory. The accuracy on the dev set was the same as reported in the [EMNLP paper](https://www.aclweb.org/anthology/2020.emnlp-main.371.pdf) (88.1), but if you try very long documents, it might be better to train your own system.
