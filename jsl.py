# !/usr/bin/env python
# -*- coding: utf-8 -*-

import arrow
from pyquery import PyQuery as pq
from requests import Session, adapters
import re, hashlib
from urllib.parse import unquote

from model import Users, Posts, Replies, Topics, TopicUser, Provs, Industry

from logbook import Logger, StreamHandler, RotatingFileHandler
import sys
log_format = '[{record.time:%Y-%m-%d %H:%M:%S}] {record.level_name}::{record.channel}[{record.module}]:{record.lineno} - {record.message}'

StreamHandler(sys.stdout, format_string=log_format, level='DEBUG').push_application()
RotatingFileHandler('log.log', format_string=log_format, max_size=1024*1024*64, backup_count=5, bubble=True).push_application()

log = Logger(__file__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36'
}

def gen_id(some):
    return int(hashlib.sha1(some.encode()).hexdigest(), 16) % (10 ** 8)

class FetchPost(object):
    def __init__(self):
        self.__session = Session()
        self.__session.mount('https://', adapters.HTTPAdapter(max_retries=3))

    def __extract_users(self, dollar):
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

    def __extract_posts(self, pid, dollar):
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

    def __extract_replies(self, pid, dollar):
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

    def single(self, pid):
        log.info('start fetching post - pid: %s' % pid)
        resp = self.__session.get('https://www.jisilu.cn/question/%s' % pid, headers=HEADERS)
        dollar = pq(resp.content)
        if('问题不存在或已被删除'.encode()) in resp.content:
            log.warn('deleted post - pid: %s' % pid)
            return

        users = self.__extract_users(dollar)
        if users:
            Users.insert_many(users.values()).on_conflict('IGNORE').execute()
        else:
            log.error('NO USER!!! - pid: %s' % pid)

        post = self.__extract_posts(pid, dollar)
        Posts.insert(post).on_conflict('IGNORE').execute()

        replies = self.__extract_replies(pid, dollar)
        if replies:
            Replies.insert_many(replies.values()).on_conflict('IGNORE').execute()
        return post

    def multi(self, op=1, ed=260052):
        for pid in range(op, ed):
            self.single(pid)


class FetchUser(object):
    def __init__(self):
        self.__session = Session()
        self.__session.mount('https://', adapters.HTTPAdapter(max_retries=3))

    def __parse_last_signin(self, dollar):
        for elem in dollar('.aw-user-center-details dl'):
            if '最后活跃' in pq(elem)('dt span').text():
                return pq(elem)('dd').text();

    def __extract_user_details(self, dollar):
        prov = dollar('i.i-user-locate + a').text().strip() or None
        prov_id = None
        if prov:
            prov_id = gen_id(prov)
        Provs.insert({
            'id': prov_id,
            'prov': prov
        }).on_conflict('IGNORE').execute()

        industry = dollar('i.i-user-post').parent().text().strip() or None
        industry_id = None
        if industry:
            industry_id = gen_id(industry)
        Industry.insert({
            'id': industry_id,
            'industry': industry
        }).on_conflict('IGNORE').execute()

        lvs = {
            'VIP': 0,
            '活跃用户': 1,
            '普通用户': 2,
            '已注销': -1,
            # '非信任用户': 1
            # '封禁用户': 0
        }
        lvk = dollar('.aw-mod-body .aw-user-center-follow-meta > span a em')

        details = {
            'name': dollar('.aw-mod-body .aw-user-title +h1').remove('img').text(),
            'signature': dollar('.aw-mod-body .aw-user-title + h1 + span').text().strip(),
            'prestige': dollar('.aw-mod-body .aw-user-center-follow-meta .i-user-prestige + em').text(),
            'approve': dollar('.aw-mod-body .aw-user-center-follow-meta .i-user-approve + em').text(),
            'thank': dollar('.aw-mod-body .aw-user-center-follow-meta .i-user-thank + em').text(),
            'coins': dollar('.aw-mod-body .aw-user-center-follow-meta i[style] + em').text().strip('+'),
            'industry': industry_id,
            'prov': prov_id,
            'visits': re.findall('\d+', (dollar('i.i-user-visits').parent().text()))[0],
            'locate': dollar('i.i-user-locate + a + a').text().strip() or None,
            'last_signin_at': self.__parse_last_signin(dollar),
            'level': lvs.get(lvk.text().strip(' »'))
        }
        return details

    def __extract_topics(self, uid, dollar):
        topics, topicusers = [], []
        elem = dollar('dd.aw-user-center-details-good-topic > div')
        for e in elem:
            tid = pq(e)('a').attr('data-id')
            topic = unquote(pq(e)('a').attr('href').split('/')[-1])
            approve, thank = pq(e).remove('a')('span').text().split(' ')
            user = uid,

            topics.append({
                'id': tid,
                'topic': topic
            })
            topicusers.append({
                'user': uid,
                'topic': tid,
                'approve': approve,
                'thank': thank
            })
        return topics, topicusers

    def single(self, uid=None, linkname=None, save=False):
        log.info('start fetching user - uid: %s | linkname: %s' % (uid, linkname))
        url = 'https://www.jisilu.cn/people/%s' % (uid or linkname)
        resp = self.__session.get(url, headers=HEADERS)
        dollar = pq(resp.content)
        if '用户不存在'.encode() in resp.content:
            log.warn('deleted user - uid: %s | linkname: %s' % (uid, linkname))
            return

        if uid:
            topics, topicusers = self.__extract_topics(uid, dollar)
            if topics:
                Topics.insert_many(topics).on_conflict('IGNORE').execute()
                TopicUser.insert_many(topicusers).on_conflict('IGNORE').execute()

        details = self.__extract_user_details(dollar)
        details.update({
            'id': uid,
            'linkname': unquote(resp.url.split('/')[-1]),
        })
        if save:
            Users.insert(detail).on_conflict('REPLACE').execute()
        return details

    def multi2(self, op=1, ed=228090, step=100):
        rcds = []
        for uid in range(op, ed):
            rcd = self.single(uid)
            if not rcd:
                continue
            rcds.append(rcd)
            if len(rcds) % step == 0:
                log.info('updating %s records' % step)
                Users.insert_many(rcds).on_conflict('REPLACE').execute()
        Users.insert_many(rcds).on_conflict('REPLACE').execute()

    def multi(self, op=1):
        users = (Users.select(Users.id)
                .where((Users.id >= op))# & (Users.last_signin_at >> None))
                .order_by(Users.id))
        for u in users:
            rcd = self.single(uid=u.id)
            if not rcd:
                continue
            Users.insert(rcds).on_conflict('REPLACE').execute()


class Pipeline(object):
    def __init__(self):
        self.post = FetchPost()
        self.user = FetchUser()


if __name__ == '__main__':
    import fire
    fire.Fire(Pipeline)
