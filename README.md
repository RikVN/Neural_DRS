# Neural DRS parsing

This folder contains scripts to use our neural seq2seq model to produce DRSs. Also, new models can be trained.

## Getting Started

```
git clone https://github.com/RikVN/Neural_DRS
cd Neural_DRS
```

### Prerequisites

You will need the Torch version of [OpenNMT](https://github.com/OpenNMT/OpenNMT) with all its dependencies. My results are with [this version](https://github.com/OpenNMT/OpenNMT/tree/2d9bc10a459bf4bd1e7ce1848e4575755c11b31c) of OpenNMT, I cannot guarantee that it works for newer versions.

```
git clone https://github.com/OpenNMT/OpenNMT/
cd OpenNMT
git checkout 2d9bc10
```

If you want to an ensemble during parsing, you will have to checkout the ensemble branch. Instructions on how to do that are [here](http://forum.opennmt.net/t/ensemble-decoding/115/11). Note that you have to specify ONMT_HOME in config/default_config.sh to the correct location of this branch. 

For evaluation and format checking we will use Counter and clf_referee.py from the [DRS_parsing respository](https://github.com/RikVN/DRS_parsing):

```
cd ../
git clone https://github.com/RikVN/DRS_parsing
```

The scripts in this section will import from clf_referee.py, so make sure DRS_parsing/evaluation/ is on your PYTHONPATH, e.g. like this:

```
export PYTHONPATH=${PYTHONPATH}:/your/folders/here/Neural_DRS/DRS_parsing/evaluation/
```

All script are written in Python 2.7. Make sure to install [psutil](https://pypi.python.org/pypi/psutil) and [pyyaml](https://pypi.org/project/PyYAML/), which can be easily done with pip.

### Configuration

In config/default_config.sh we store the default settings for preprocessing, training and parsing. All shell scripts read from there. **You will have to set the correct paths in config/default_config.sh.** The scripts need to know where your OpenNMT folder is and where this repository is located.

If you do not have access to GPU, you'll have to change the gpuid setting as well.

### Running from OpenNMT

**IMPORTANT:** You have to run the training and parsing scripts with the OpenNMT directory as your working folder. We will assume that the OpenNMT folder is located in this Github folder when giving instructions on how to run. If you put the OpenNMT folder somewhere else, you'll have to change where preprocessing.sh, train.sh and parse.sh read default_config.sh from.

## Parsing

If you only want to do parsing, please download (one of) our [pre-trained models](http://www.let.rug.nl/rikvannoord/DRS/models/). Please select the GPU or CPU models depending on what your setup is. You can choose between our best gold-only models, or our best model in general, that is also trained on the silver data released in PMB 2.1.0.

When using one of those models, you will have to preprocess the input to the input structure the model expects.

For all the models there, SENT_FILE should not be tokenized, and then put in char-level format, with relative naming of the variables and a feature indicating casing:

```
python src/preprocess.py -s SENT_FILE -c feature -v rel -r char --sents_only
```

Then do the parsing. If you specify multiple models, it will automatically be an ensemble, **but this easily gets out of memory for longer, non-PMB input**. The config file to use for both the models is config/parse_best_config.sh. Note that this config-file can only be used for parsing, not training. 

You need to open the config file and also default_config.sh to enter the specific settings of your own computer. Then, run the parser like this:

```
../src/parse.sh ../config/parse_best_config.sh INPUT_FILE OUTPUT_FILE MODEL1 [MODEL2] [MODEL3] ...
```

The output will be automatically postprocessed to a valid CLF format. Invalid DRSs will be replaced by dummy (but valid) ones.

Note that these models were trained on mainly short sentences (up to 15 tokens). Most likely they won't perform that well for long sentences.

## Training

For training, you can apply our pre- and postprocessing scripts. Note that you are not necessarily dependent on OpenNMT for the training, but I'll give those examples here.

### Getting data ###

If you cloned the [DRS_parsing repository](https://github.com/RikVN/DRS_parsing), you'll have the train and dev set for PMB release 2.1.0 available. Otherwise, download a [PMB release](http://pmb.let.rug.nl/data.php) and construct the training data yourself, or use some other data set.

### Config files ###

You already set up config/default_config.sh. That contains all our default settings for experiments. However, if you want to run your own experiments you have to set your own parameters. The config/ folder already contains an example for our baseline model you can finish.

Make sure that you specify a folder for the experiment (will be created) where all information (models, input, output, vocab) is saved. Also, specify where the train and dev data is located.

### Running the system ###

Then, preprocess the data:

```
cd OpenNMT
../src/preprocess.sh ../config/baseline.sh
```

If there are no errors, you can train like this:

```
../src/train.sh ../config/baseline.sh
```

This will most likely take some time. If training is finished, you can parse new files in the following way:

```
../src/parse.sh ../config/baseline.sh INPUT_FILE OUTPUT_FILE MODEL1 [MODEL2] [MODEL3] ...
```

The output will be automatically postprocessed. You can only use multiple models if you obtained the ensemble branch of OpenNMT (see above).

If you parsed the PMB 2.1.0 development set, you can calculate an F-score by using Counter:

```
python ../DRS_parsing/evaluation/counter.py -f1 CLF_OUTPUT -f2 ../DRS_parsing/data/dev.txt
```

The baseline model should score somewhere between 72 and 74 in F-score. You can create your own config files to perform different experiments.

## Output ##

If you're only interested in the output of our parser(s), please check the **output/** folder. We have added parser on the PMB 2.1.0 development set for the following parsers:

| Parser				           | F-score	| Info |
| ------- | ------- | ------- | 
| seq2seq best char model      | 83.6         | our best character-level model (gold + silver) |
| seq2seq best word model      | 83.1         | our best word-level model (gold + silver)  |
| seq2seq best char gold only  | 77.9         | our best character-level model (gold-only)  |
| seq2seq best word gold only | 75.1         | our best word-level model (gold-only)
| Boxer                       | 74.3         | output of the semantic parser Boxer |
| amr2drs                     | 41.8         | output of a rule-based parser that converts AMRs to DRSs |
| SIM-SPAR                    | 56.8         | baseline - outputs the DRS most similar DRS in the train set |
| SPAR                        | 39.7         | baseline parser that outputs a fixed DRSs for each sentence |

The baseline parsers SPAR and amr2drs are available in the [DRS_parsing repository](https://github.com/RikVN/DRS_parsing).

## Author

* **Rik van Noord** - PhD-student at University of Groningen - [Personal website](http://www.rikvannoord.nl)

## Citation ##

We are currently publishing a paper regarding our models and the CLF referee, when published the link will be here.

If you use Counter, please cite our [LREC paper](http://www.let.rug.nl/rob/doc/lrec2018.pdf):

Rik van Noord, Lasha Abzianidze, Hessel Haagsma, and Johan Bos, 2018. **Evaluating scoped meaning representations**. In Proceedings of the Eleventh International Conference on Language Resources and Evaluation (LREC 2018), Miyazaki, Japan

@inproceedings{vanNoordLREC:2018,  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; title = {Evaluating Scoped Meaning Representations}  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; author    = {van Noord, Rik and Abzianidze, Lasha and Haagsma, Hessel and Bos, Johan},  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; booktitle = {Proceedings of the Eleventh International Conference on Language Resources and Evaluation (LREC 2018)},  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; address   = {Miyazaki, Japan},  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; year      = {2018}  
}  

## Acknowledgments

* Thanks to all members of the [Parallel Meaning Bank](http://pmb.let.rug.nl)
