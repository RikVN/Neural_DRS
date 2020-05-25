# Neural DRS parsing

This folder contains scripts to use our neural seq2seq model to produce DRSs. It contains code to reproduce either our [TACL paper](https://www.mitpressjournals.org/doi/abs/10.1162/tacl_a_00241) or our [IWCS paper](https://www.aclweb.org/anthology/W19-0504/). The first one relies on [OpenNMT](http://opennmt.net/), while the second one relies on [Marian](https://marian-nmt.github.io/). 

If you just want the best parser, use the Marian models, and just ignore the section about OpenNMT in this README.

## Getting Started

```
git clone https://github.com/RikVN/Neural_DRS
cd Neural_DRS
```

This repository works with PMB release. If you want to work with 2.2.0 (or older), run this:

```
git checkout v2.2.0-final
```

### Prerequisites

I advise creating a Conda environment to install the dependencies. My own Python scripts are for Python 3.

You will need either the Torch version of [OpenNMT](https://github.com/OpenNMT/OpenNMT) or [Marian](https://marian-nmt.github.io/) **with all their dependencies**. Also, if you want to use the Marian parser of the [IWCS paper](https://www.aclweb.org/anthology/W19-0504/), you will have to install software to get the linguistic features ([CoreNLP](https://stanfordnlp.github.io/CoreNLP/download.html), [easyCCG](https://github.com/ParallelMeaningBank/easyccg)).

I made a script ``setup.sh`` that handles installation of all software (though I'm not sure about all the dependencies):

```
./src/setup.sh
```

This will also clone the [DRS_parsing respository](https://github.com/RikVN/DRS_parsing), which contains the DRS data and evaluation scripts. The scripts in this section will import from clf_referee.py, so make sure DRS_parsing/evaluation/ is on your $PYTHONPATH, e.g. like this:

```
export PYTHONPATH=${PYTHONPATH}:/your/folders/here/Neural_DRS/DRS_parsing/evaluation/
```

If you want to use an ensemble during parsing for OpenNMT, you will have to checkout the ensemble branch. Instructions on how to do that are [here](http://forum.opennmt.net/t/ensemble-decoding/115/11). Note that you have to specify $ONMT_HOME in config/opennmt/default_config.sh to the correct location of this branch. 

Note: if you want to run Marian on CPU, check out [this fork](https://github.com/dhgoratela/Neural_DRS) by [dhgoratela](https://github.com/dhgoratela) and especially [this script](https://github.com/dhgoratela/Neural_DRS/blob/v2.2.0-marian-cpu/src/marian_cpu_preset.sh).
<<<<<<< HEAD
=======

>>>>>>> 7614b0daf3d044a046f63ce297ea2e49d1f5437b

### Configuration

In config/opennmt/default_config.sh and config/marian/default_config.sh we store the default settings for preprocessing, training and parsing. All shell scripts read from there. **You will have to set the correct paths yourself.** The scripts need to know where the current repo is located, and perhaps other locations are also different on your machine.

If you do not have access to GPU, you'll have to change the gpuid setting as well (all my experiments are on GPU, not sure if it will work).

### Getting data ###

In the [DRS_parsing repository](https://github.com/RikVN/DRS_parsing), you'll find the train and dev set for PMB release 2.1.0 and 2.2.0 available. You can also download a [PMB release](http://pmb.let.rug.nl/data.php) and construct the training data yourself, or use some other data set. Note that our scripts expect the train and dev data to be in the same folder.

### Testing your setup ###

If you want to check that everything is installed/downloaded/setup correctly, simply run this:

```
./src/unit_tests.sh
```

This does a range of tests for the OpenNMT and Marian experiments and can only succeed if everything works.

## Running with OpenNMT ##

First I'll describe how to run experiments with OpenNMT, which we described in [this paper](https://www.mitpressjournals.org/doi/abs/10.1162/tacl_a_00241)

## Running from OpenNMT folder

**IMPORTANT:** You have to run the training and parsing scripts with the OpenNMT directory as your working folder. We will assume that the OpenNMT folder is located in this Github folder when giving instructions on how to run. If you put the OpenNMT folder somewhere else, you'll have to change where preprocess.sh, train.sh and parse.sh read default_config.sh from!

### Parsing raw text

If you only want to do parsing, please download (one of) our [pre-trained models](http://www.http://www.let.rug.nl/rikvannoord/DRS/TACL/models/). If you ran ``setup.sh``, the GPU models should already be downloaded. You can choose between our best gold-only models, or our best model in general, that is also trained on the silver data released in PMB 2.1.0.

When using one of those models, you will have to preprocess the input to the input structure the model expects.

For all the models there, $SENT_FILE should not be tokenized, and then put in char-level format, with a feature indicating casing:

```
python src/preprocess.py -s $SENT_FILE -c feature -r char --sents_only
```

Then do the parsing. If you specify multiple models, it will automatically be an ensemble, **but this easily gets out of GPU memory for longer, non-PMB input**. The config file to use for both the models is config/opennmt/parse_best_config.sh. Note that this config-file can only be used for parsing, not training. 

Make sure to check default_config.sh and parse_best_config.sh to make sure your local folders are set correctly. Then, run the parser like this:

```
cd OpenNMT
../src/opennmt_scripts/parse.sh ../config/opennmt/parse_best_config.sh $INPUT_FILE $OUTPUT_FILE $MODEL1 [$MODEL2] [$MODEL3] ...
```

The output will be automatically postprocessed to a valid CLF format. Invalid DRSs will be replaced by dummy (but valid) ones.

Note that these models were trained on mainly short sentences (up to 15 tokens). Most likely they won't perform that well for long sentences.

### Training

You already set up config/opennmt/default_config.sh. That contains all our default settings for experiments. However, if you want to run your own experiments you have to set your own parameters. The config folder already contains an example for our baseline model you can finish (config/opennmt/baseline.sh).

Make sure that you specify a folder for the experiment (will be created) where all information (models, input, output, vocab, logs) is saved. Also, specify where the train and dev data is located. **Every experiment needs such a config file!**

The examples here are for sample data, just to show that it works. Start by preprocessing the data:

```
cd OpenNMT
../src/opennmt_scripts/preprocess.sh ../config/opennmt/sample.sh
```

If there are no errors, you can train like this:

```
../src/opennmt_scripts/train.sh ../config/opennmt/sample.sh
```

This will most likely take some time. If training is finished, you can parse new files in the following way:

```
../src/opennmt_scripts/parse.sh ../config/opennmt/sample.sh $INPUT_FILE $OUTPUT_FILE $MODEL1 [$MODEL2] [$MODEL3] ...
```

Noe that the input file should be in the correct character-level format (src/preprocess.py). The output will be automatically postprocessed. You can only use multiple models if you are using the ensemble branch of OpenNMT (see above).

If you parsed a gold standard dev/test set, you can calculate an F-score by using Counter:

```
python ../DRS_parsing/evaluation/counter.py -f1 $CLF_OUTPUT -f2 $GOLD_DEV
```

The baseline model should score somewhere between 74 and 76 in F-score. You can create your own config files to perform different experiments.

## Running with Marian ##

Again, make sure that config/marian/default_config.sh contains the correct paths on your setup.

### Linguistic features ###

The models trained with Marian can use linguistic features (but don't have to necessarily). We use [CoreNLP](https://stanfordnlp.github.io/CoreNLP/download.html), [easyCCG](https://github.com/ParallelMeaningBank/easyccg) and the TNT tagger (Semantic tags) to obtain the features. Running ``setup.sh`` should take care of the first two, but for TNT you need to fill in [a license](http://www.coli.uni-saarland.de/~thorsten/tnt/) to get the system (sorry). Our best model only uses lemmas, though, so having the tagger is only necessary to reproduce my gold-only results. Also, you could potentially replace it with your own tagger.

You can extract all the linguistic features (lem/pos/dep/sem/ccg) using ``src/marian_scripts/extract_ling_features.sh``, like this:

```
./src/marian_scripts/extract_ling_features.sh $SENT_FILE
```

$SENT_FILE should not be tokenized already, we use CoreNLP to do that. If $TNT is not set in the default config, it simply skips semtagging.

As we do in the paper, it is possible to combine features in a single input file. You can merge them like this:

``
python src/merge_tags.py -f ${SENT_FILE}.pos ${SENT_FILE}.dep ${SENT_FILE}.ccg ${SENT_FILE}.lem --char_exts .lem > ${SENT_FILE}.multi
``

By using --char_exts you specify which files (by extension) should be in character-level representation. In our setup, this only makes sense for the lemmas.

**Note**: if you don't want to bother with linguistic features, you can use our baseline gold + silver model for the parsing (baseline_gold_silver.sh), which is only slightly worse than using the features.

### Parsing from raw text ###

If you're only interested in parsing from raw text, please download one of our [pretrained models](http://www.let.rug.nl/rikvannoord/DRS/IWCS/models/). Probably you want to use our best model, which is gold + silver with lemmas as extra linguistic features (best_gold_silver). Again, ``setup.sh`` should have already handled this (check models/).

First extract the linguistic features for you sentence file as described above, using ``extract_ling_features.sh``.

Then, for our best silver model, you have to preprocess the lemma features to a char-level representation.

```
python src/merge_tags.py -f ${SENT_FILE}.lem --char_exts .lem > ${SENT_FILE}.clem
```

The parse script will automatically take care of preprocessing the raw sentence file, using the settings as described in the specific config file.

Now to the actual parsing. You have to use the config file that fits with the model you chose, i.e. use config/marian/best_gold_silver.sh if you use our best silver model. Obviously, fill in the variables yourself, depending on where you put the file(s):

```
./src/marian_scripts/parse_raw_text.sh config/marian/best_gold_silver.sh $PRETRAINED_MODEL $OUTPUT_FILE $SENT_FILE ${SENT_FILE}.clem
```

This will automatically postprocess your file to ${OUTPUT_FILE}.res. Also, ${OUTPUT_FILE}.res.log will contain information about this process.

### Training your own model ###

The script ``src/marian_scripts/pipeline.sh`` can be used to run your own experiments. Again, note that each experiment needs its own config file. I have added examples of config files in config/marian/, which can also be used to train our best gold-only and best general model.

**Make sure that the models have access to the files with linguistic features**, as is described above. In config/marian/default_config.sh you can see which settings can be overwritten to create different experiments.

Some things to note: if $PRETRAINED_FOLDER and $FINETUNED_FOLDER are both set, it automatically does pretraining + finetuning. If you only want "normal" training, leave $FINETUNED_FOLDER empty. Our best silver model can simply be reproduced by this:

```
./src/marian_scripts/pipeline.sh config/marian/best_gold_silver.sh
```

## Output ##

If you're only interested in the output of our parser(s), please check the **output/** folder.  We have added parser output on the development set for PMB release 2.1.0, and dev + test for PMB release 2.2.0/3.0.0.


### PMB release 2.1.0 ###


| Parser				           | F-score	| Info |
| ------- | ------- | ------- | 
| ONMT: best char model      | 83.6         | our best character-level model (gold + silver) |
| ONMT: best word model      | 83.1         | our best word-level model (gold + silver)  |
| ONMT: best char gold only  | 77.9         | our best character-level model (gold-only)  |
| ONMT: best word gold only  | 75.1         | our best word-level model (gold-only) |
| Boxer                       | 74.3         | output of the semantic parser Boxer |
| amr2drs                     | 43.2         | output of a rule-based parser that converts AMRs to DRSs |
| SIM-SPAR                    | 56.8         | baseline - outputs the DRS in the train set most similar to current DRS |
| SPAR                        | 39.7         | baseline parser that outputs a fixed DRS for each sentence |

The baseline parsers SPAR and amr2drs are available in the [DRS_parsing repository](https://github.com/RikVN/DRS_parsing).

### PMB release 2.2.0 ###

These are the results from [this paper](https://www.aclweb.org/anthology/W19-0504/). Though if you use --fix during postprocessing, the scores will increase a bit. See our [shared task submission](https://www.aclweb.org/anthology/W19-1204/) for more details.

| Parser				      | F1-dev	| F1-test |  Info |
| ------- | ------- | ------- | ------- |
| Marian: best gold + silver  | 85.6        | 87.0        | our best word-level model (gold + silver)  |
| Marian: best gold-only      | 81.3        | 83.4        | our best character-level model (gold-only) |
| ONMT best model             | 80.9        | 83.2        | Best OpenNMT model retrained on PMB-2.2.0 |
| Boxer                       | 72.2        | 72.2        | output of the semantic parser Boxer |
| SIM-SPAR                    | 53.3        | 57.7        | baseline - outputs the DRS in the train set most similar to current DRS |
| SPAR                        | 40.0        | 40.8        | baseline parser that outputs a fixed DRS for each sentence |


### PMB release 3.0.0 ###

I retrained the OpenNMT and Marian systems + baselines on the 3.0.0 data. Output files are available in output/. Boxer is trained using a better role labeler, which explains the increase in performance.

| Parser				      | F1-dev	| F1-test |
| ------- | ------- | ------- | ------- |
| Marian best model  | 86.8  | 87.7        |
| ONMT best model    | 84.3       | 84.9        |
| Boxer              | 78.2       | 78.8       |
| SIM-SPAR           | 54.9     | 59.2      |
| SPAR               | 40.9       | 42.1        |


## Author

* **Rik van Noord** - PhD-student at University of Groningen - [Personal website](http://www.rikvannoord.nl)

## Citation ##

This directory is part of our [TACL](https://www.mitpressjournals.org/doi/abs/10.1162/tacl_a_00241) and [IWCS paper](https://www.aclweb.org/anthology/W19-0504/):

van Noord, R., Abzianidze, L., Toral, A., & Bos, J. (2018). **Exploring Neural Methods for Parsing Discourse Representation Structures.** *Transactions Of The Association For Computational Linguistics*, 6, 619-633

Rik van Noord, Antonio Toral and Johan Bos. (2019) **Linguistic Information in Neural Semantic Parsing with Multiple Encoders** IWCS 2019

If you use Counter, please cite our [LREC paper](https://arxiv.org/pdf/1802.08599.pdf):

Rik van Noord, Lasha Abzianidze, Hessel Haagsma, and Johan Bos, 2018. **Evaluating scoped meaning representations**. *In Proceedings of the Eleventh International Conference on Language Resources and Evaluation (LREC 2018)*, Miyazaki, Japan

## Acknowledgments

* Thanks to all members of the [Parallel Meaning Bank](http://pmb.let.rug.nl)
