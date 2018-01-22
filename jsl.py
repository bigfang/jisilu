# !/usr/bin/env python
# -*- coding: utf-8 -*-

import arrow
from pyquery import PyQuery as pq
from requests import Session
from urllib.parse import unquote

from model import Users, Posts, Replies, Topics, TopicUser


from logbook import Logger, StreamHandler, RotatingFileHandler
import sys
log_format = '[{record.time:%Y-%m-%d %H:%M:%S}] {record.level_name}::{record.channel}[{record.module}]:{record.lineno} - {record.message}'

StreamHandler(sys.stdout, format_string=log_format, level='DEBUG').push_application()
RotatingFileHandler('log.log', format_string=log_format, max_size=4096, backup_count=5, bubble=True).push_application()

log = Logger(__file__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36'
}

session = Session()
START = 261924
END = 261928

def fetch_reply():
    pass

def fetch_post(pid):
    resp = session.get('https://www.jisilu.cn/question/%s' % pid, headers=HEADERS)
    dollar = pq(resp.content)
    # with open('ppp.html', 'r') as f:
    #     dollar = pq(f.read())
    user = {
        'id': dollar('a.aw-user-name').attr('data-id'),
        'name': dollar('.aw-side-bar a.aw-user-name').text(),
        'linkname': unquote(dollar('.aw-side-bar a.aw-user-name').text().split('/')[-1]),
    }
    u = Users.insert(user).execute()

    last_actived_at, views, focus = [pq(i).text() for i in dollar('.aw-side-bar-mod-body li span')]
    post = {
        'id': pid,
        'user': u,
        'title': dollar('.aw-mod-head h1').text(),
        'content': dollar('.aw-mod-body .aw-question-detail-txt').remove('div').text().strip(),
        'updated_at': dollar('.aw-question-detail-meta span.pull-left').text(),
        'views': views,
        'focus': focus,
        'last_actived_at': last_actived_at
    }
    p = Posts.insert(post).execute()


def run():
    for pid in range(START, END):
        fetch_post(pid)
        break


if __name__ == '__main__':
    run()
