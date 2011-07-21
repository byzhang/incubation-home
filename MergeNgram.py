#!/usr/bin/env python

import codecs
import heapq
from optparse import OptionParser
import utils


def main():
    parser = OptionParser(conflict_handler='resolve')
    parser.add_option('--type', default='cn', help='cn|en')
    parser.add_option('--min_freq', default='2', help='')
    (options, args) = parser.parse_args()
    min_freq = int(options.min_freq)

    iters = (utils.NgramIter(codecs.open(x, encoding='utf-8', mode='r'), True) for x in args)
    l = apply(heapq.merge, tuple(iters))
    cur_ngram = ''
    cur_count = 0
    for ngram, count in l:
        if ngram != cur_ngram:
            if cur_ngram != '' and cur_count >= min_freq:
                print cur_ngram.encode('utf-8'), cur_count
            cur_ngram = ngram
            cur_count = int(count)
        else:
            cur_count += int(count)
    if cur_count >= min_freq:
        print cur_ngram.encode('utf-8'), cur_count
    return


if __name__ == '__main__':
    main()
