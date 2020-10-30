# DRS Jury #

DRS Jury is a DRS parsing evaluation tool that has the same capabilities as Counter, plus a lot more:

* Averaging over multiple output files (recommended to do this)
* Comparing different experiments easily
* Individual scores per clause type (e.g. F-score on just predicting "Agent")
* Analysis of performance on infrequent word senses
* F-score over sentence-length plots
* Statistical tests between two experiments
* Semantic tag analysis (e.g. how well do we score on negation)
* Listing the hardest documents per experiment
* Listing the relatively easiest/hardest documents compared to the other experiment
* Individual analysis of these documents, with example output per document

Here, I will give a more detailed overview of how to use DRS jury.

## Parameter options ##

I will list the most important parameter options here. Parameter options specific to one of the capabilities above will be handles separately.

* -f, --folders List the folders that contain DRS output. Can also be single files!
* -p, --prefix All output files need to start with this prefix.
* -de, --drs_ext Extension of the output files we will find in the folder
* -w, --working Working folder in which we save results.
* -n, --names Names of the experiments, for nicer printing
* -s, --sentences Raw sentences of the output (default 3.0.0 English dev)
* -d, --dev_drss Gold standard DRS file of the output (default 3.0.0 English dev)
* -td, --train_drss Gold standard train DRSs, needed for infrequent sense analysis (default 3.0.0 English train)
* -w, --wait_for_input Don't do full analysis at once, wait for user input (enter) to continue

There are a few options that you can often leave to the default:

* -c, --counter Location of Counter (default DRS_parsing/evaluation/counter.py)
* -sig, --sig_file Location of signature file of referee (default DRS_parsing/evaluation/clf_signature.yaml)
* -th, --threads Number of Counter parallel threads (default 8)
* -sgn, --significant Significant numbers (default 3)

## Running DRS Jury ##

An example of calling DRS Jury, for which the defaults are correct:

```
python src/drs_jury.py --folders output/pmb-3.0.0/en/dev/bert_only/ output/pmb-3.0.0/en/dev/bert_char_1enc/ --prefix output -de .txt --working tst/unit/ --names bert_only bert_char_1enc
```

This will compare the output of two of our experiments, between the BERT-only model and the model that used BERT plus characters in one encoder.

Since both experiments have 5 output files, it needs to run quite a lot of Counter experiments first. However, once the files exist, the script will not regenerate them.

Let's examine the output. First, it outputs the "standard" Counter output (with some extra scores). But now those are averaged over 5 output files!

<pre>
                  bert_only   bert_char_1enc
Prec              0.888       0.889
Rec               0.864       0.873
F1                0.876       0.881
Operators         0.95        0.954
Roles             0.89        0.89
Concepts          0.847       0.849
....
# exp 1 > exp 2   257         324
# exp 1 == exp 2  304         304
</pre>

After that, it gives averaged scores over individual operators, roles and concepts:

<pre>
Clause          Gold inst   bert_only   bert_char_1enc
PRESUPPOSITION  977         0.96        0.966
EQU             460         0.934       0.935
TPR             414         0.977       0.979
NEGATION        73          0.955       0.956
...
</pre>

<pre>
Clause  Gold inst   bert_only   bert_char_1enc
Time    870         0.968       0.971
Theme   463         0.83        0.843
Agent   373         0.922       0.927
Name    365         0.883       0.881
...
</pre>

Of course you don't have to report all these scores. It's just to give a more detailed indication of model performance. You can decide for yourself which scores are interesting.

### Comparing clause scores ###

When comparing two experiments, the script offers a method to automatically list the clauses for which performance differed the most between experiments. The clauses should occur at least 10 times in the gold standard, as to flood the results with infrequent concepts. It returns 5 (alter with --ret) of these clauses, like this:

<pre>
Clauses for which bert_only > bert_char_1enc has the most difference:

Clause        	Gold inst 	bert_only 	bert_char_1enc 	Diff  
ClockTime     	13        	0.774     	0.592          	0.182 
location.n.01 	15        	0.91      	0.823          	0.087 
Colour        	13        	0.944     	0.882          	0.062 
Creator       	17        	0.775     	0.732          	0.043 
Topic         	18        	0.659     	0.617          	0.042 

Clauses for which bert_char_1enc > bert_only has the most difference:

Clause        	Gold inst 	bert_only 	bert_char_1enc 	Diff   
YearOfCentury 	12        	0.621     	0.764          	-0.143 
Causer        	11        	0.415     	0.553          	-0.138 
desire.v.01   	10        	0.788     	0.909          	-0.121 
Result        	22        	0.72      	0.797          	-0.077 
Manner        	15        	0.641     	0.713          	-0.072 
</pre>
 

### Infrequent sense analysis ###

A subtask of DRS parsing is word sense disambiguation. A concept clause can only match if it matches the word **and** the word sense. It is interesting to look at the clauses in the gold standard dev set that were **not** the most frequent in the training set. In other words, the concepts for which the model has to do something else than outputting the default most frequent sense. Especially the score for "Combined" is interesting:

<pre>
Clause      Gold inst   bert_only   bert_char_1enc
Combined    215         0.549       0.576
be.v.02     30          0.817       0.841
be.v.01     20          0.639       0.659
have.v.02   8           0.667       0.603
...
</pre>

### Semantic tag analysis ###

For this to work, you need to have specified --layer_data. This expects the semtags in CoNLL format, as provided [here](https://github.com/RikVN/DRS_parsing/tree/master/parsing/layer_data/gold/en). The default is the English dev set for 3.0.0.

First, it gives scores per subset of sentences that contain a single semtag:

<pre>
Tag 	Docs 	bert_only 	bert_char_1enc 
NIL 	786  	0.879     	0.885          
CON 	513  	0.865     	0.870          
PRO 	401  	0.889     	0.893          
REL 	287  	0.864     	0.865          
NOW 	275  	0.882     	0.888          
EPS 	268  	0.883     	0.889
....
</pre>

Then, it gives scores for the subset of sentences that contain at least a single semtag out of list of semtags that represent a certain (semantic) phenomenon. Details can be found in our EMNLP paper.

<pre>
Exp            	Docs 	bert_only 	bert_char_1enc 
All            	885  	0.876     	0.881          
Modal          	100  	0.869     	0.868          
  Negation     	77   	0.895     	0.895          
  Possibility  	23   	0.784     	0.790          
  Necessity    	9    	0.788     	0.783          
Logic          	209  	0.856     	0.863          
Pronouns       	497  	0.882     	0.885
...
</pre>

A more general analysis can be found in this [README](Semtags.md). You can define your own experiments in [src/semtag_analysis.py](src/semtag_analysis.py).

### Sentence length plot ###

It's also interesting to see how well models do on longer sentences. The script automatically generates a sentence length plot. If you ran setup.sh, you can find the plot in
tst/unit/senlen_plot.pdf. These parameters are of interest:

* -t, --tokenized_sentences Important: tokenized sentences of gold output, default PMB 3.0.0 dev
* -m, --min_occurrence Minimum number of times a certain sen-length should occur (default 8)
* -mi, --min_sen_len Minimum sentence length that we want to plot from (default 3)
* -p, --plot_file Location of sentence length plot (default working folder + senlen_plot.pdf)

### Statistical test ###

We do approximate randomization to check whether two experiments differ significantly from each other. Some explanation of this method can be found [here](http://cs.stanford.edu/people/wmorgan/sigtest.pdf). A significant difference is found when the p-value is smaller than 0.05. Though, if you run a lot of experiments, perhaps that value needs to be corrected for. We used 1000 randomizations in our experiments, but you can change this value with --randomizations. In our case, we find that BERT + char (1enc) is significantly better than BERT-only:

<pre>
Do statistical testing with approximate randomization (1000 runs)

bert_only better than bert_char_1enc: p-value of 0.997
bert_char_1enc better than bert_only: p-value of 0.003
</pre>

### Hardest documents ###

Then, the script gives the 5 (alter with --ret) hardest documents for each experiment. In other words, the documents with the lowest F-score, not counting ill-formed DRSs. This might give you some insight in what the models fail to learn.

<pre>
5 worst sentences for bert_only:

0.0 Look out!
0.0 Fire burns.
0.175 The dove symbolizes peace.
...
</pre>

### Relatively easy/hard documents ###

If you compare two experiments, the script also returns the 5 (alter with --ret) documents that are relative easy/hard for the first experiment. This looks like this (index, F-score, sentence):

<pre>
Sentences for which exp1 has most positive difference with exp2:

541 0.4 He devoted his life to his company.
768 0.321 Alas!
82 0.234 How blue the sky is!
...

Sentences for which exp1 has most negative difference with exp2:

597 -0.682 Oil this bicycle.
283 -0.353 I'm fed up with this winter, I want spring right now!
867 -0.308 All the passengers died, but he survived.
...
</pre>

### Individual analysis of easy/hard documents ###

The previous lines did not gives us that much information about what the model did, exactly. You probably want to get a bit more insight in what the models output, exactly, and how that compared to the gold standard. You can specify this by using the -a, --analyse_indices parameter. For example, -a 0 1 2 will give these detailed results for the easiest **and** hardest documents. It outputs the gold standard, example output for exp1, example output for exp2 and a detailed overview of matching clauses:

<pre>
Detailed scores for largest diff DRS 0 (idx 541) - avged over 5 files
Sentence: He devoted his life to his company.

Gold DRS:

b3 REF e1             % devoted [3...10]
b3 REF t1             % devoted [3...10]
b3 Agent e1 x1        % devoted [3...10]
b3 TPR t1 "now"       % devoted [3...10]
b3 Theme e1 x2        % devoted [3...10]
...

Example output for bert_only:

b1 REF x1
b1 REF x2
b1 Agent x1 x5
b1 TPR x2 "now"
b1 Theme x1 x3
...

Example output for bert_char_1enc:

b1 REF x1
b1 REF x2
b1 Agent x1 x5
b1 TPR x2 "now"
b1 Theme x1 x3
b1 Time x1 x2
b1 devote "v.01" x1
....

Clause                	Gold inst 	bert_only 	bert_char_1enc
PRESUPPOSITION        	3         	0.857     	0.364
Owner                 	2         	0.462     	0.333
TPR                   	1         	1.0       	0.75
Agent                 	1         	1.0       	0.75
Theme                 	1         	0.909     	0.75
Time                  	1         	1.0       	0.75
Goal                  	1         	1.0       	0.333
.....
</pre>
