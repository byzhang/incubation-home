#!/usr/bin/env python

import codecs
from optparse import OptionParser
import utils


def main():
    parser = OptionParser(conflict_handler='resolve')
    parser.add_option('--type', default='cn', help='cn|en')
    parser.add_option('--min_freq', default=6, help='')
    parser.add_option('--max_ngram', default=6, help='')
    (options, args) = parser.parse_args()
    min_freq = int(options.min_freq)
    max_ngram = int(options.max_ngram)

    iter = utils.NgramIter(codecs.open(args[0], encoding='utf-8', mode='r'), True)
    all_count = 0
    for ngram, count in iter:
        count = int(count)
        if utils.GoodNgram(ngram, count, options.type, min_freq, max_ngram):
            print ngram.encode('utf-8'), count
            all_count += count
    print 'ALLCOUNT', all_count


if __name__ == '__main__':
    main()
