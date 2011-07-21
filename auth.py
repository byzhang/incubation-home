#!/usr/bin/env python

import utils


def main():
    fetcher = utils.Weibo()
    fetcher.auth()


if __name__ == '__main__':
    main()
