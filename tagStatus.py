#!/usr/bin/env python
# -*- coding:UTF-8 -*-

# Just run a single instance

from optparse import OptionParser
import hashlib
import io
import os
import redis
import time
import utils


def main():
    parser = OptionParser(conflict_handler='resolve')
    parser.add_option('--ngram', default='', help='prefix of ngram files')
    parser.add_option('--weight', default='', help='prefix of ngram weight files')
    parser.add_option('--bad', default='', help='prefix of bad ngram files')
    parser.add_option('--unigram', default='', help='unigram file')
    parser.add_option('--stop', default='', help='stop ngram files')
    parser.add_option('--authors', default='王矛,尚巷骆驼,丁晓诚', help='authors to tag')
    parser.add_option('--userid', default='0', help='')
    (options, _) = parser.parse_args()
    authors = options.authors.split(',')

    cn_scorer = utils.Scorer('cn', options.ngram + '.cn', options.weight + '.cn', options.unigram, options.bad, options.stop)
    en_scorer = utils.Scorer('en', options.ngram + '.en', options.weight + '.en', options.unigram, options.bad, options.stop)

    fetcher = utils.Weibo()
    fetcher.setToken(int(options.userid))

    segmenter = utils.StatusSegmenter()
    cleaner = utils.Cleaner()

    pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
    r = redis.Redis(connection_pool=pool)

    id_key = 'friends-tag-id'
    text_key = 'friends-id'

    version = 'V2'
    num_comment = 0
    sleep_time = 1.0
    while True:
        while True:
            r.watch(id_key)

            # get start_id, end_id
            start_id = r.get(id_key)
            if start_id == None:
                start_id = '0'
            end_id = r.get(text_key)
            start = int(start_id)
            end = min(start + 50, int(end_id))

            # get keys and status
            if end - start < 30:
                r.unwatch()
                sleep_time += 1
                time.sleep(sleep_time)
                continue
            sleep_time = max(1, sleep_time/2)

            keys = ['friends-%d' % x for x in xrange(start, end)]
            print 'processing', start, end
            lines = r.mget(keys)

            for line in lines:
                if line == None:
                    continue
                (line, id) = utils.ExtractTextID(line, authors)
                if line == u'':
                    continue
                print '==============='
                print line.encode('utf-8')
                all_segments = []
                texts = segmenter.segment(line)
                for text in texts:
                    # process each segment
                    text = text.strip()
                    sentences = cleaner.clean(text)
                    for s in sentences:
                        # process each sentence in en or in cn
                        s = s.strip()
                        if s == u'':
                            continue
                        if utils.IsEn(s[0]):
                            en_scorer.compute(s)
                            segments = en_scorer.get()
                        else:
                            cn_scorer.compute(s)
                            segments = cn_scorer.get()
                        all_segments.extend(segments)
                good_segments = utils.GoodPhrases(all_segments, 4.5, 6)
                if len(good_segments) == 0:
                    continue
                comments = u' '.join([u'#%s# (%d)' % (y, x) for x, y in good_segments])
                comments = u'%d %s %s' % (id, version, comments)
                comments = comments.encode('utf-8')
                print comments
                sleep_time2 = 10
                while True:
                    try:
                        time.sleep(sleep_time2)
                        fetcher.comment(id, comments)
                        pass
                    except Exception, e:
                        print e
                        sleep_time2 += 2
                        print 'sleep', sleep_time2
                        pass
                    else:
                        break

            # update redis
            pipe = r.pipeline()
            pipe.set(id_key, end)
            try:
                pipe.execute()
            except redis.exceptions.WatchError, e:
                # retry this text
                print 'retry'
                pass
            else:
                # break, and process next text
                print 'complete processing'
                break


if __name__ == '__main__':
    main()
