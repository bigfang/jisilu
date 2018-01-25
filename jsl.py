# !/usr/bin/env python
# -*- coding: utf-8 -*-

import fire
import arrow
from pyquery import PyQuery as pq
from requests import Session
from urllib.parse import unquote

from model import db, Users, Posts, Replies, Topics, TopicUser

from logbook import Logger, StreamHandler, RotatingFileHandler
import sys
log_format = '[{record.time:%Y-%m-%d %H:%M:%S}] {record.level_name}::{record.channel}[{record.module}]:{record.lineno} - {record.message}'

StreamHandler(sys.stdout, format_string=log_format, level='DEBUG').push_application()
RotatingFileHandler('log.log', format_string=log_format, max_size=1024*1024*64, backup_count=5, bubble=True).push_application()

log = Logger(__file__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36'
}

class Jisilu(object):
    def __init__(self):
        self.session = Session()

    def _extract_users(self, dollar):
        users = {}
        for u in dollar('a.aw-user-name'):
            user = {
                pq(u).attr('data-id'): {
                    'id': pq(u).attr('data-id'),
                    'name': pq(u).text(),
                    'linkname': unquote(pq(u).text().split('/')[-1])
                }
            }
            users.update(user)
        return users

    def _extract_posts(self, pid, dollar):
        last_actived_at, views, focus = None, None, None
        if dollar('.aw-side-bar-mod-body li span'):
            last_actived_at, views, focus = [pq(i).text() for i in dollar('.aw-side-bar-mod-body li span')]
        else:
            log.warn('closed Post - pid: %s' % pid)
        post = {
            'id': pid,
            'user': dollar('a.aw-user-name').attr('data-id'),
            'title': dollar('.aw-mod-head h1').text(),
            'content': dollar('.aw-mod-body .aw-question-detail-txt').remove('div').text().strip(),
            'updated_at': dollar('.aw-question-detail-meta span.pull-left').text(),
            'views': views,
            'focus': focus,
            'last_actived_at': last_actived_at
        }
        return post

    def _extract_replies(self, pid, dollar):
        replies = {}
        ele = dollar('.aw-mod-body.aw-dynamic-topic .aw-item')
        if not ele:
            log.warn('no replies - pid: %s' % pid)
            return
        for r in ele:
            rid = pq(r).attr('id').split('_')[-1]
            reply = {
                rid : {
                    'id': rid,
                    'post': pid,
                    'content': pq(r)('.markitup-box').text(),
                    'updated_at': pq(r)('.aw-dynamic-topic-meta span.pull-left').text(),
                    'user': pq(r)('.aw-user-name').attr('data-id')
                }
            }
            replies.update(reply)
        return replies

    def fetch_posts(self, pid):
        log.info('start fetch - pid: %s' % pid)
        resp = self.session.get('https://www.jisilu.cn/question/%s' % pid, headers=HEADERS)
        dollar = pq(resp.content)
        if('问题不存在或已被删除'.encode()) in resp.content:
            log.warn('deleted post - pid: %s' % pid)
            return

        users = self._extract_users(dollar)
        if users:
            Users.insert_many(users.values()).on_conflict('IGNORE').execute()
        else:
            log.error('NO USER!!! - pid: %s' % pid)

        post = self._extract_posts(pid, dollar)
        Posts.insert(post).on_conflict('IGNORE').execute()

        replies = self._extract_replies(pid, dollar)
        if replies:
            Replies.insert_many(replies.values()).on_conflict('IGNORE').execute()

    def post(self, op=1, ed=260052):
        for pid in range(op, ed):
            self.fetch_posts(pid)

    def user(self):
        pass


if __name__ == '__main__':
    fire.Fire(Jisilu)
