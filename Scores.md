# Scores on DRS parsing #

Here, we list the scores of our models on DRS parsing for English, German, Italian and Dutch, for PMB releases 2.1.0, 2.2.0 and 3.0.0. The scores are F-scores calculated by [Counter](https://www.aclweb.org/anthology/L18-1267.pdf). If you want to do a more detailed evaluation, please see [DRS Jury](DRS_jury.md).

## PMB 2.1.0 - English ##

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

The baseline parsers SPAR and amr2drs are available in the [DRS_parsing repository](https://github.com/RikVN/DRS_parsing). ONMT models are described in [this paper](https://www.aclweb.org/anthology/Q18-1043.pdf).

## PMB 2.2.0 - English ##

This includes results from [this paper](https://www.aclweb.org/anthology/W19-0504/) (Marian) and the latest [EMNLP paper](https://www.aclweb.org/anthology/2020.emnlp-main.371.pdf) (AllenNLP). It includes systems that use BERT, and combine BERT and characters, and a system that employs semtags. Note that Marian and AllenNLP (BERT) scores are averaged over 5 runs of the system.

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


## PMB 3.0.0 - English ##

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


## Non-English 2.2.0 ##

We also have scores for German, Italian and Dutch DRS parsing.

| Parser				      | de-dev	| de-test | it-dev	| it-test | nl-dev	| nl-test |
| ------- | ------- | ------- | ------- | ------- | ------- | ------- |
| BERT + char (two encoders)  | 69.8 | 71.8 | 74.0 | 77.1 | 65.9 | 65.7 |
| BERT + char (one encoder)  | 69.3 | 70.8 | 73.8 | 76.3 | 66.3 | 65.2 |
| BERT-only                   | 66.6 | 69.0 | 71.9 | 73.3 | 66.0 | 63.7 |
| Characters-only			  | 63.1 | 66.4 | 68.3 | 71.7 | 61.5 | 60.6 |

## Non-English 3.0.0 ##


| Parser				      | de-dev	| de-test | it-dev	| it-test | nl-dev	| nl-test |
| ------- | ------- | ------- | ------- | ------- | ------- | ------- |
| BERT + char (two encoders)  | 82.4 | 82.0 | 80.2 | 80.5 | 71.8 | 71.2 |
| BERT + char (one encoder)   | 81.9 | 81.3 | 79.2 | 80.5 | 71.6 | 71.8 |
| BERT-only                   | 80.2 | 79.5 | 77.4 | 79.0 | 71.4 | 71.2 |
| Characters-only			  | 80.4 | 79.4 | 77.7 | 79.0 | 68.7 | 69.1 |
