#!/usr/bin/env python
# -*- coding: utf8 -*-

'''Train a CRF sequence tagger based on classical features
   NOTE: files have to be in PMB CoNLL format, as you can find here:
   https://github.com/RikVN/DRS_parsing/tree/master/parsing/layer_data'''

import argparse
from sklearn_crfsuite import CRF
from sklearn_crfsuite import metrics
import joblib
from semtag_analysis import read_conll_data
from uts import write_to_file


def create_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--objective", type=str, choices=["train", "parse"], default="parse",
                        help="Are we training or parsing?")
    parser.add_argument("-t", "--train_file", type=str,
                        help="Input file for training, not needed when parsing")
    parser.add_argument("-te", "--test_file", type=str,
                        help="For parsing, this should be a file of tokenized (!) sentences \
                              For training, this is a file in CoNLL format to determine accuracy")
    parser.add_argument("-m", "--model", type=str,
                        help="Model to use during parsing OR location we save trained model to")
    parser.add_argument("-min", "--min_freq", type=int, default=2,
                        help="Minimal number of occurences for the CRF model to add a feature")
    parser.add_argument("-out", "--output_file", type=str,
                        help="File we write the semtags to when parsing")
    args = parser.parse_args()
    if args.objective == "train" and not args.train_file:
        raise ValueError("For training, --train_file needs to be specified")
    if args.objective == "parse" and not args.test_file:
        raise ValueError("For parsing, --test_file needs to be specified")
    if args.objective == "parse" and not args.output_file:
        raise ValueError("For parsing, --output_file needs to be specified")
    return args


def ngram_feature(sentence, idx, n):
    '''Return the n-gram for a certain n, sentence and index where the n-gram should start'''
    if idx < 0:  # start too early
        return ''
    if idx + n > len(sentence) - 1:  # end too late
        return ''
    return " ".join(sentence[idx:idx+n])


def add_ngram_features(feat_dict, sentence, idx):
    '''Add unigram, bigram and trigram features as features for a sentence'''
    feat_dict['cur_word'] = ngram_feature(sentence, idx, 1)
    feat_dict['prev_word'] = ngram_feature(sentence, idx-1, 1)
    feat_dict['two_prev_word'] = ngram_feature(sentence, idx-2, 2)
    feat_dict['next_word'] = ngram_feature(sentence, idx+1, 1)
    feat_dict['two_next_word'] = ngram_feature(sentence, idx+2, 2)
    feat_dict['bigram_forward'] = ngram_feature(sentence, idx, 2)
    feat_dict['bigram_backward'] = ngram_feature(sentence, idx-1, 2)
    feat_dict['trigram_forward'] = ngram_feature(sentence, idx, 3)
    feat_dict['trigram_middle'] = ngram_feature(sentence, idx-1, 3)
    feat_dict['trigram_backward'] = ngram_feature(sentence, idx-2, 3)
    # 4-grams and 5-grams are commented out for now as they did not improve performance for me
    # You could use them though in your experiments
    # Fourgrams
    #feat_dict['fourgram1'] = ngram_feature(sentence, idx, 4)
    #feat_dict['fourgram2'] = ngram_feature(sentence, idx-1, 4)
    #feat_dict['fourgram3'] = ngram_feature(sentence, idx-2, 4)
    #feat_dict['fourgram4'] = ngram_feature(sentence, idx-3, 4)
    ## And fivegrams
    #feat_dict['fivegram1'] = ngram_feature(sentence, idx, 5)
    #feat_dict['fivegram2'] = ngram_feature(sentence, idx-1, 5)
    #feat_dict['fivegram3'] = ngram_feature(sentence, idx-2, 5)
    #feat_dict['fivegram4'] = ngram_feature(sentence, idx-3, 5)
    #feat_dict['fivegram5'] = ngram_feature(sentence, idx-4, 5)
    return feat_dict


def features(sentence, index):
    '''Add features for a certain sentence + index of the word we are looking at
       Classical binary features, prefix/suffix features and n-gram features'''
    feat_dict = {
        # Character-level features
        'prefix-1': sentence[index][0],
        'prefix-2': sentence[index][:2],
        'prefix-3': sentence[index][:3],
        'suffix-1': sentence[index][-1],
        'suffix-2': sentence[index][-2:],
        'suffix-3': sentence[index][-3:],
        # Binary features
        'has_hyphen': '-' in sentence[index],
        'is_numeric': sentence[index].isdigit(),
        'capitals_inside': sentence[index][1:].lower() != sentence[index][1:],
        'is_first': index == 0,
        'is_last': index == len(sentence) - 1,
        'is_capitalized': sentence[index][0].upper() == sentence[index][0],
        'is_all_caps': sentence[index].upper() == sentence[index],
        'is_all_lower': sentence[index].lower() == sentence[index]
    }
    # Ngram features up to trigrams (around index)
    feat_dict = add_ngram_features(feat_dict, sentence, index)
    return feat_dict


def build_dataset(sents):
    '''Build a featurized dataset from the sentences and labels'''
    all_feats = []
    for sent in sents:
        feats = []
        for idx, word in enumerate(sent):
            # Token-features, ngrams + classic binary features
            feats.append(features(sent, idx))
        all_feats.append(feats)
    return all_feats


def train(train_file, test_file, min_freq, model_file):
    '''Train a CRF tagger based'''
    # Read in initial training data
    conll_data_train = read_conll_data(train_file)
    train_sents = [[line[0] for line in doc] for doc in conll_data_train]
    train_labels = [[line[2] for line in doc] for doc in conll_data_train]

    # Featurize and create instance from list of sentences
    feat_sent_train = build_dataset(train_sents)
    print("Training on {0} inst".format(len(feat_sent_train)))

    # Train and test loop for parameter settings
    # Create and train CRF model
    # For different parameter options, see:
    # https://sklearn-crfsuite.readthedocs.io/en/latest/_modules/sklearn_crfsuite/estimator.html
    model = CRF(min_freq=min_freq)
    model.fit(feat_sent_train, train_labels)

    # Test the model on held out test set if wanted
    if args.test_file:
        conll_data_test = read_conll_data(test_file)
        test_sents = [[line[0] for line in doc] for doc in conll_data_test]
        test_labels = [[line[2] for line in doc] for doc in conll_data_test]
        feat_sent_test = build_dataset(test_sents)
        # Predicting and printing accuracy
        pred = model.predict(feat_sent_test)
        acc = metrics.flat_accuracy_score(test_labels, pred)
        print("Accuracy: {0}%".format(float(round(acc, 3)) * 100))
    # Save model to disk if wanted
    if args.model:
        print("Saving model to {0}".format(model_file))
        joblib.dump(model, model_file)


def parse(test_file, model_file, output_file):
    '''Parse with pretrained semtag model a file of sentences'''
    # Load sents and featurize
    sentences = [x.strip().split() for x in open(test_file, 'r')]
    feats = build_dataset(sentences)
    # Load model
    model = joblib.load(model_file)
    # Do predictions
    pred = model.predict(feats)
    # Write predictions to file
    write_to_file([" ".join(sem) for sem in pred], output_file)


if __name__ == "__main__":
    args = create_arg_parser()
    if args.objective == "train":
        train(args.train_file, args.test_file, args.min_freq, args.model)
    else:
        parse(args.test_file, args.model, args.output_file)
