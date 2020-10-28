# Neural DRS parsing

This folder contains scripts to use our neural seq2seq model to produce DRSs. It contains code to reproduce either our [TACL paper](https://www.mitpressjournals.org/doi/abs/10.1162/tacl_a_00241), our [IWCS paper](https://www.aclweb.org/anthology/W19-0504/) or our EMNLP paper. The models rely on [OpenNMT](http://opennmt.net/), [Marian](https://marian-nmt.github.io/) and [AllenNLP](https://allennlp.org/), respectively.

Information about reproducing the specific papers are in separate READMEs. This README helps in setting up all DRS parsing experiments.

## Getting Started

```
git clone https://github.com/RikVN/Neural_DRS
cd Neural_DRS
```

This repository works with PMB release 3.0.0. If you want to work with 2.2.0 (or older), run this:

```
git checkout v2.2.0-final
```

### Setup

First we will setup the datasets and the [DRS_parsing respository](https://github.com/RikVN/DRS_parsing), which is needed for evaluation.

I made a script ``setup.sh`` that takes care of this. Throughout the README I assume you ran this.

```
./src/setup.sh
```

Make sure DRS_parsing/ and DRS_parsing/evaluation/ is on your $PYTHONPATH, e.g. like this:

```
cur_dir=$(pwd)
export PYTHONPATH=${cur_dir}/DRS_parsing/:${PYTHONPATH}
export PYTHONPATH=${cur_dir}/DRS_parsing/evaluation/:${PYTHONPATH}
```

You can find the data in data/ now. You can also download a [PMB release](http://pmb.let.rug.nl/data.php) and construct the training data yourself.

### Testing your setup ###

We want to be sure that all scripts that are independent of your (neural) parsing software work. This includes preprocessing, postprocessing, Counter and DRS jury. This command should succeed without errors:

```
./src/unit_tests.sh
```

## DRS Jury ##

Explanation coming soon, it's available in src/.

## Running experiments ##

For each of the three papers, I have written separate READMEs. Please find the links below:

* [TACL paper with OpenNMT](OpenNMT.md)
* [IWCS paper with Marian](Marian.md)
* EMNLP paper with AllenNLP (coming soon)

## Scores & Output ##

If you're only interested in the output of our parser(s), please check the **output/** folder.  We have added parser output for release 2.1.0, 2.2.0 and 3.0.0. Marian en AllenNLP (BERT) scores are averaged over 5 runs of the system.

### PMB 2.1.0 - English ###

| Parser | Dev	|
| ------- | ------- |
| ONMT: best char model       | 83.6 |
| ONMT: best word model       | 83.1 |
| ONMT: best char gold only   | 77.9 |
| ONMT: best word gold only   | 75.1 |
| Boxer                       | 74.3 |
| amr2drs                     | 43.2 |
| SIM-SPAR                    | 56.8 |
| SPAR                        | 39.7 |

The baseline parsers SPAR and amr2drs are available in the [DRS_parsing repository](https://github.com/RikVN/DRS_parsing).

### PMB 2.2.0 - English ###

This includes results from [this paper](https://www.aclweb.org/anthology/W19-0504/) (Marian) and the latest EMNLP paper (AllenNLP). It includes systems that use BERT, and combine BERT and characters, and a system that employs semtags.

| Parser				      | Dev	| Test |
| ------- | ------- | ------- |
| BERT + char + semtags (two encs) | 85.5 | 87.7 |
| BERT + char (two encoders)  |  85.6 | 88.1 |
| BERT + char (one encoders)  | 86.1 | 88.3 |
| BERT-only                   | 85.4 | 87.9 |
| Marian: best gold + silver  | 85.6 | 87.0 |
| Marian: best gold-only      | 81.3 | 83.4 |
| ONMT best model             | 80.9 | 83.2 |
| Boxer                       | 72.2 | 72.2 |
| SIM-SPAR                    | 53.3 | 57.7 |
| SPAR                        | 40.0 | 40.8 |


### PMB 3.0.0 - English ###

Similar models as for 2.2.0. Boxer is trained using a better role labeler, which explains the increase in performance.

| Parser				      | Dev	| Test |
| ------- | ------- | ------- |
| BERT + char + semtags (two encs) | 88.4 | 89.3 |
| BERT + char (two encoders)  | 88.1 | 89.0 |
| BERT + char (one encoder)  | 88.1 | 89.2 |
| BERT-only                   | 87.6 | 88.5 |
| Marian best model  | 86.8 | 87.7 |
| ONMT best model    | 84.3 | 84.9 |
| Boxer              | 78.2 | 78.8 |
| SIM-SPAR           | 54.9 | 59.2 |
| SPAR               | 40.9 | 42.1 |


### Non-English 2.2.0 ###

We also have scores for German, Italian and Dutch DRS parsing.

| Parser				      | de-dev	| de-test | it-dev	| it-test | nl-dev	| nl-test |
| ------- | ------- | ------- | ------- | ------- | ------- | ------- |
| BERT + char (two encoders)  | 69.8 | 71.8 | 74.0 | 77.1 | 65.9 | 65.7 |
| BERT + char (one encoder)  | 69.3 | 70.8 | 73.8 | 76.3 | 66.3 | 65.2 |
| BERT-only                   | 66.6 | 69.0 | 71.9 | 73.3 | 66.0 | 63.7 |
| Characters-only			  | 63.1 | 66.4 | 68.3 | 71.7 | 61.5 | 60.6 |

### Non-English 3.0.0 ###


| Parser				      | de-dev	| de-test | it-dev	| it-test | nl-dev	| nl-test |
| ------- | ------- | ------- | ------- | ------- | ------- | ------- |
| BERT + char (two encoders)  | 82.4 | 82.0 | 80.2 | 80.5 | 71.8 | 71.2 |
| BERT + char (one encoder)   | 81.9 | 81.3 | 79.2 | 80.5 | 71.6 | 71.8 |
| BERT-only                   | 80.2 | 79.5 | 77.4 | 79.0 | 71.4 | 71.2 |
| Characters-only			  | 80.4 | 79.4 | 77.7 | 79.0 | 68.7 | 69.1 |

## Author

* **Rik van Noord** - PhD-student at University of Groningen - [Personal website](http://www.rikvannoord.nl)

## Citation ##

This directory is part of our [TACL](https://www.mitpressjournals.org/doi/abs/10.1162/tacl_a_00241), [IWCS paper](https://www.aclweb.org/anthology/W19-0504/) and EMNLP paper:

van Noord, R., Abzianidze, L., Toral, A., & Bos, J. (2018). **Exploring Neural Methods for Parsing Discourse Representation Structures.** *Transactions Of The Association For Computational Linguistics*, 6, 619-633

Rik van Noord, Antonio Toral and Johan Bos. (2019) **Linguistic Information in Neural Semantic Parsing with Multiple Encoders** IWCS 2019

If you use Counter, please cite our [LREC paper](https://arxiv.org/pdf/1802.08599.pdf):

Rik van Noord, Lasha Abzianidze, Hessel Haagsma, and Johan Bos, 2018. **Evaluating scoped meaning representations**. *In Proceedings of the Eleventh International Conference on Language Resources and Evaluation (LREC 2018)*, Miyazaki, Japan

## Acknowledgments

* Thanks to all members of the [Parallel Meaning Bank](http://pmb.let.rug.nl)
