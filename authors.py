#!/usr/bin/env python

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
    (options, _) = parser.parse_args()

    pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
    r = redis.Redis(connection_pool=pool)

    id_key = 'friends-author-id'
    text_key = 'friends-id'

    sleep_time = 1.0
    while True:

        while True:
            authors = {}
            orig_authors = {}

            r.watch(id_key)

            # get start_id, end_id
            start_id = r.get(id_key)
            if start_id == None:
                start_id = '0'
            end_id = r.get(text_key)
            start = int(start_id)
            end = min(start + 500, int(end_id))

            # get keys and status
            if end - start < 20:
                r.unwatch()
                sleep_time += 1
                time.sleep(sleep_time)
                continue
            sleep_time = max(1, sleep_time / 2.0)
            keys = ['friends-%d' % x for x in xrange(start, end)]
            print 'processing', start, end
            lines = r.mget(keys)

            for line in lines:
                if line == None:
                    continue
                (author, orig_author) = utils.ExtractAuthors(line)
                if author in authors:
                    authors[author] += 1
                else:
                    authors[author] = 1
                if orig_author == '':
                    continue
                if orig_author in orig_authors:
                    orig_authors[orig_author] += 1
                else:
                    orig_authors[orig_author] = 1

            # update redis
            pipe = r.pipeline()
            pipe.set(id_key, end)
            for k, v in authors.items():
                pipe.zincrby('authors', k, v)
            for k, v in orig_authors.items():
                pipe.zincrby('orig-authors', k, v)
            try:
#                time.sleep(sleep_time)
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
