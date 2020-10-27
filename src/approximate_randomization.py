#!/usr/bin/env python
# -*- coding: utf8 -*-

'''Do statistical test -- approximate randomization
   http://cs.stanford.edu/people/wmorgan/sigtest.pdf

   Files should only contain scores, one score per line'''

import argparse
import random
from uts import load_float_file


def create_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f1", required=True, type=str, help="First file with scores")
    parser.add_argument("-f2", required=True, type=str, help="Second file with scores")
    parser.add_argument("-r", default=1000, type=int, help="Number of randomizations")
    return parser.parse_args()


def sign_test(x_scores, y_scores, randomizations):
    '''Do the random approximation significance test here'''
    assert len(x_scores) == len(y_scores), "Number of DRSs prod/gold not equal, {0} vs {1}" \
                                           .format(len(x_scores), len(y_scores))
    init_tvalue = len([x for x, y in zip(x_scores, y_scores) if x > y])
    higher = 0

    # Loop over number of randomizations
    for _ in range(0, randomizations):
        new_x = []
        new_y = []
        for x, y in zip(x_scores, y_scores):
            # Do the randomization here
            if random.choice([True, False]):
                new_x.append(x)
                new_y.append(y)
            else:
                new_x.append(y)
                new_y.append(x)

        t_value = len([x for x, y in zip(new_x, new_y) if x > y])
        if t_value > init_tvalue:
            higher += 1
    # Calculate final p-value here
    p_value = float((1 + higher)) / float((1 + randomizations))
    return p_value


if __name__ == '__main__':
    args = create_arg_parser()
    res = sign_test(load_float_file(args.f1), load_float_file(args.f2), args.r)
    print("p-value of {0}".format(res))
