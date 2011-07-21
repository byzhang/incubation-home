#!/usr/bin/dev python
# -*- coding:UTF-8 -*-

from weibopy.auth import OAuthHandler, BasicAuthHandler
from weibopy.api import API
import codecs
import math
import re
import string
import sys
import unicodedata as u
import unittest
import utils


class Weibo(unittest.TestCase):

    app_key = "2337929492"
    app_secret ="70a4afeebf195f5e483fee4de3f35442"

    # 9: byzhang9@qq.com, 汇源微博: follow sources
    # 1: byzhang1@qq.com, 源汇微博: accept users, and follow back
    # 2: benyu_zhang@hotmail.com: testing
    # 0: byzhang0@qq.com, 源微博: forward @
    token = {
            0: 'bf28d4db071c70c684f95bbf4a6c6157',
            1: 'fcdd42c5f842972e11ad57ffab57f66f',
            2: 'b4074040f104645e66e20c785695e782',
            9: 'd5450b992600f9459f7295b97cd782ed',
            }
    tokenSecret = {
            0: '4e4dbb038c50ffe1c1d7bb567f6daeeb',
            1: '42d8f51f9ebfa07d15a0e655bc62e8ce',
            2: 'f3af990ff923cd3b561a5a6a6db76f06',
            9: 'bb545269719c81de3a97712963eb9037',
            }

    def __init__(self):
        """ constructor """
        self.fetched_ids = []


    def getAtt(self, key):
        try:
            return self.obj.__getattribute__(key)
        except Exception, e:
            return u''


    def getAttValue(self, obj, key):
        try:
            return obj.__getattribute__(key)
        except Exception, e:
            return u''


    def basicAuth(self, source, username, password):
        self.auth = BasicAuthHandler(username, password)
        self.api = API(self.auth,source=source)


    def initAPI(self):
        self.api = API(source=self.app_key)


    def setToken(self, userid):
        self.auth = OAuthHandler(self.app_key, self.app_secret)
        self.auth.setToken(self.token[userid], self.tokenSecret[userid])
        self.api = API(self.auth)


    def auth(self):
        self.auth = OAuthHandler(self.app_key, self.app_secret)
        auth_url = self.auth.get_authorization_url()
        print 'Please authorize: ' + auth_url
        verifier = raw_input('PIN: ').strip()
        self.auth.get_access_token(verifier)
        self.api = API(self.auth)


    def comment(self, id=11930515524, comment='#Test#@丁晓诚'):
        self.obj = self.api.comment(id=id, comment=comment, without_mention=1)
        mid = self.getAtt("id")
        return mid


    def public_timeline(self, pages=1):
        cur_ids = []
        texts = []
        for page in xrange(1, pages + 1):
            timeline = self.api.public_timeline(count=200, page=page)
            if len(timeline) == 0:
                if page != pages:
                    # Don't call for next pages
#                    sys.stderr.write('stop @page %d\n' % page)
                    pass
                break
            id_fetched = False
            for line in timeline:
                self.obj = line
                mid = self.getAtt("id")
                if mid in cur_ids:
#                    sys.stderr.write('same id in the same fetch\n')
                    continue
                cur_ids.append(mid)
                if mid in self.fetched_ids:
                    id_fetched = True
                    continue
                text = self.getAtt("text")
                if text:
                    texts.append(text)
            if id_fetched:
                if page != pages:
                    # Don't call for next pages
#                    sys.stderr.write('stop @page %d\n' % page)
                    pass
                break
        self.fetched_ids = cur_ids
        return texts


    def friends_timeline(self, pages=1):
        cur_ids = []
        texts = []
        for page in xrange(1, pages + 1):
            timeline = self.api.friends_timeline(count=200, page=page)
            if len(timeline) == 0:
                if page != pages:
                    # Don't call for next pages
#                    sys.stderr.write('stop @page %d\n' % page)
                    pass
                break
            id_fetched = False
            for line in timeline:
                self.obj = line
                mid = self.getAtt("id")
                if mid in cur_ids:
#                    sys.stderr.write('same id in the same fetch\n')
                    continue
                cur_ids.append(mid)
                if mid in self.fetched_ids:
                    id_fetched = True
                    continue
                texts.append(repr(line))
            if id_fetched:
                if page != pages:
                    # Don't call for next pages
#                    sys.stderr.write('stop @page %d\n' % page)
                    pass
                break
        self.fetched_ids = cur_ids
        return texts


    def friends(self):
        cursor = -1
        users = []
        while cursor != 0:
            results = self.api.friends(cursor=cursor, count=200)
            cursor = results['next_cursor']
            for user in results['users']:
                users.append(user.screen_name)
        return users


    def follow(self, screenname):
        return self.api.create_friendship(screen_name=screenname)


def ExtractAuthors(line):
    status = eval(line)
    author = status['author']
    orig_author = ''
    if status['retweeted'] != '':
        orig_author = status['retweeted']['author']
    return (author, orig_author)


def ExtractTextID(line, authors_filter=[]):
    status = eval(line)
    if len(authors_filter) > 0 and status['author'] not in authors_filter:
        return (u'', 0)
    line = status['text']
    if status['retweeted'] != '':
        line += ' / ' + status['retweeted']['text']
    return (unicode(line, encoding='utf-8'), status['id'])


def ExtractText(line, source):
    if source == 'friends':
        status = eval(line)
        line = status['text']
        if status['retweeted'] != '':
            line += ' / ' + status['retweeted']['text']
    return unicode(line, encoding='utf-8')


def RemoveUrl(s):
    return re.sub('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', r" ", s)


def RemoveIcon(s):
    return re.sub('\[.+\]', r" ", s)


class StatusSegmenter(object):

    def __init__(self):
        pass


    def segment(self, s):
        s = s.strip()
        s = RemoveUrl(s)
        s = RemoveIcon(s)
        return s.split(u'/')


def IsEn(s):
    return ((u'0' <= s) and (s <= u'9')) or \
           ((u'A' <= s) and (s <= u'Z')) or \
           ((u'a' <= s) and (s <= u'z'))


def IsECJKChar(c):
    if (ord(u'0') <= c) and (c <= ord(u'9')):
        return True
    if (ord(u'a') <= c) and (c <= ord(u'z')):
        return True
    if (ord(u'A') <= c) and (c <= ord(u'Z')):
        return True
    if (0x4E00 <= c) and (c <= 0x9FBB):
        return True
    return False


def GenerateNgrams(tokens, min_ngram, max_ngram, sep, ngrams):
    for i in xrange(0, len(tokens)):
        for j in xrange(i + min_ngram, 1 + min(len(tokens), i + max_ngram)):
            ngram = sep.join(tokens[i:j])
#            print 'NGRAM', ngram.encode('utf-8')
            if ngram in ngrams:
                ngrams[ngram] += 1
            else:
                ngrams[ngram] = 1


class Cleaner(object):

    def __init__(self):
        self.table = dict((i, unichr(i).lower()) for i in xrange(ord(u'A'), ord(u'Z') + 1))
        self.table.update(dict((i, u' ') for i in range(65536) if not IsECJKChar(i)))
        self.table[ord(u'的')] = u' '
        self.table[ord(u'了')] = u' '
        self.table[ord(u'啊')] = u' '
        self.table[ord(u'呢')] = u' '
        self.table[ord(u'们')] = u' '
        self.table[ord(u'这')] = u' '
        self.table[ord(u'么')] = u' '


    def separate_en_cn(self, s):
        results = []
        if len(s) == 0:
            return [u'']
        r = s[0]
        prev_en = IsEn(s[0])
        for x in xrange(1, len(s)):
            cur_en = IsEn(s[x])
            if prev_en:
                if cur_en or s[x] == u' ':
                    r += s[x]
                else:
                    results.append(r)
                    prev_en = False
                    r = s[x]
            else:
                if cur_en or s[x] == u' ':
                    results.append(r)
                    prev_en = True
                    r = s[x]
                else:
                    r += s[x]
        results.append(r)
        return results


    def clean(self, s):
        """
        s is unicode, and already segmented.
        """
        try:
            s = s.translate(self.table)
        except Exception, e:
            print type(s)
            print s
            print e
            return [u'']
        s = s.strip()
        return self.separate_en_cn(s)


def GoodNgram(ngram, count, type, min_freq, max_ngram):
    if min_freq != None and count < min_freq:
        return False
    if type == 'en':
        if len(ngram.split(u' ')) > max_ngram:
            return False
    elif type == 'cn':
        if len(ngram) > max_ngram:
            return False
    else:
        return False
    return True


class NgramIter(object):

    def __init__(self, iter, unicode=False):
        self.iter = iter
        self.unicode = unicode

    def __iter__(self):
        return self

    def next(self):
        try:
            line = self.iter.next()
            if not self.unicode:
                line = unicode(line, encoding='utf-8')
        except Exception as e:
            raise StopIteration
        else:
            fields = line.strip().rsplit(u' ', 1)
            if fields[0] == '':
                print 'line', line.encode('utf-8')
            if len(fields) != 2:
                print 'wrong format'
                raise StopIteration
            else:
                return (fields[0], fields[1])


class NgramIter1(object):

    def __init__(self, iter, unicode=False):
        self.iter = iter
        self.unicode = unicode

    def __iter__(self):
        return self

    def next(self):
        try:
            line = self.iter.next()
            if not self.unicode:
                line = unicode(line, encoding='utf-8')
        except Exception as e:
            raise StopIteration
        else:
            fields = line.strip().rsplit(u' ', 1)
            if fields[0] == '':
                print 'line', line.encode('utf-8')
            if len(fields) != 2:
                print 'wrong format'
                raise StopIteration
            else:
                return (fields[0], '1', fields[1])


class NgramIter2(object):

    def __init__(self, iter, unicode=False):
        self.iter = iter
        self.unicode = unicode

    def __iter__(self):
        return self

    def next(self):
        try:
            line = self.iter.next()
            if not self.unicode:
                line = unicode(line, encoding='utf-8')
        except Exception as e:
            raise StopIteration
        else:
            fields = line.strip().rsplit(u' ', 1)
            if fields[0] == '':
                print 'line', line.encode('utf-8')
            if len(fields) != 2:
                print 'wrong format'
                raise StopIteration
            else:
                return (fields[0], '2', fields[1])


class Ngram(object):

    def __init__(self, type, ngram_file, min_freq, max_ngram):
        self.counts = {}
        self.all_counts = 0
        iter = NgramIter(codecs.open(ngram_file, encoding='utf-8', mode='r'), True)
        for ngram, count in iter:
            count = float(count)
            if ngram == 'ALLCOUNT':
                self.all_counts = count
            elif GoodNgram(ngram, count, type, min_freq, max_ngram):
                self.counts[ngram] = count

    def count(self, s, default = 0):
        return self.counts.get(s, default)

    def all_count(self):
        return self.all_counts


class Scorer(object):

    def __init__(self, type, ngram_file, weight_file, unigram_file, bad_ngram_file, stop_ngram_file, min_freq=1, max_ngram=10):
        self.type = type
        self.s = []
        self.scores = []
        self.boundaries = []
        self.stop_ngram = []
        if stop_ngram_file != '':
            file = codecs.open(stop_ngram_file, encoding='utf-8', mode='r')
            self.stop_ngram = [line.strip() for line in file]
        self.unigram = None
        if unigram_file != '':
            self.unigram = Ngram(type, unigram_file, 0, 1)
        self.bad_ngram = None
        if bad_ngram_file != '':
            self.bad_ngram = Ngram(type, bad_ngram_file, None, max_ngram)
        self.ngram = Ngram(type, ngram_file, min_freq, max_ngram)
        self.weight = Ngram(type, weight_file, min_freq, max_ngram)


    def compute(self, s, min_freq=1, min_ngram=1, max_ngram=10):
        """
        If min_ngram is greater than 1, then unigram is disabled.
        """
        if self.type == 'en':
            s = s.split(u' ')

        self.s = s
        self.scores = []
        self.boundaries = []
        for x in xrange(len(s)):
            self.scores.append([0] * (len(s) - x + 1))
            self.boundaries.append([0] * (len(s) - x + 1))

        for y in xrange(min_ngram, len(s) + 1):
            for x in xrange(len(s) + 1 - y):
                score = self.score(s, x, y, min_freq, max_ngram)
                if score > self.scores[x][y]:
                    self.scores[x][y] = score
                    self.boundaries[x][y] = 0
                for i in xrange(1, y):
                    score = self.scores[x][i] + self.scores[x+i][y-i]
                    if score > self.scores[x][y]:
                        self.scores[x][y] = score
                        self.boundaries[x][y] = i


    def yweight(self, y):
#        return pow(y, y)
#        if y == 2:
#            return pow(y, 2)
#        if y == 3:
#            return pow(y, 2.5)
#        return pow(y, 3)
        return pow(y, y/2.0 + 1)


    def score(self, s, x, y, min_freq, max_ngram):
        if y > max_ngram:
            return 0
        # unigram?
        if y == 1:
            if self.unigram == None:
                return 0
            return self.unigram.count(s[x])
        if self.type == 'en':
            token = u' '.join(s[x:x+y])
        else:
            token = s[x:x+y]
        # bad ngram?
        if self.bad_ngram != None:
            count = self.bad_ngram.count(token, 1)
            if count <= 0:
                # all bad ngrams have negative weights
                return count
        # normal ngram
        count = self.ngram.count(token)
        if count < min_freq:
            return 0
        return self.yweight(y) * count


    def get(self, x=0, y=-1):
        if y == -1:
            y = len(self.scores)
        score = self.scores[x][y]
        if score == 0:
            return []
        boundary = self.boundaries[x][y]
        if boundary == 0:
            if self.type == 'en':
                token = u' '.join(self.s[x:x+y])
            else:
                token = self.s[x:x+y]
            if token in self.stop_ngram:
                return []
            score = self.yweight(y) * self.weight.count(token, 0) / score * y * y
            return [(score, token)]
        left_results = self.get(x, boundary)
        right_results = self.get(x + boundary, y - boundary)
        results = []
        if left_results != []:
            results.extend(left_results)
        if right_results != []:
            results.extend(right_results)
        return results


def GoodPhrases(all, score_threshold=4, topk=7):
    all.sort(reverse=True)
    good = []
    cur_y = ''
    cur_x = 0
    for x, y in all:
        if x <= 0:
            continue
        if cur_y == '':
            cur_y = y
            cur_x = x
            continue
        if y == cur_y:
            cur_x += x * x * 1.0 / (cur_x + x)
            continue
        good.append((cur_x, cur_y))
        cur_y = y
        cur_x = x
    if cur_y != '':
        good.append((cur_x, cur_y))
    good.sort(reverse=True)
    return [(x, y) for x, y in good[0:topk] if x > score_threshold]
