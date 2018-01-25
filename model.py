# !/usr/bin/env python
# -*- coding: utf-8 -*-

from peewee import *
from playhouse.migrate import *
from datetime import datetime

try:
    raise ImportError
    import conf
    import psycopg2
    from playhouse.pool import PooledPostgresqlExtDatabase

    db = PooledPostgresqlExtDatabase(
        conf.dbname,
        max_connections=8,
        stale_timeout=300,
        user=conf.user,
        host=conf.host,
        password=conf.passwd,
        autorollback=True,
        register_hstore=False)
    migrator = PostgresqlMigrator(db)
except ImportError:
    db = SqliteDatabase('db.sqlite')
    migrator = SqliteMigrator(db)


class BaseModel(Model):
    class Meta:
        database = db


class Provs(BaseModel):
    id = BigIntegerField(null=False, primary_key=True, verbose_name='id')
    prov = CharField(null=True, unique=True, verbose_name='省份')


class Industry(BaseModel):
    id = BigIntegerField(null=False, primary_key=True, verbose_name='id')
    industry = CharField(null=False, unique=True, verbose_name='行业')


class Users(BaseModel):
    id = BigIntegerField(null=False, primary_key=True, verbose_name='id')
    name = CharField(max_length=255, null=False, verbose_name='用户名')
    linkname = CharField(max_length=255, unique=True, null=False, verbose_name='链接名')
    signature = CharField(max_length=1023, null=True, verbose_name='签名')

    prestige = IntegerField(null=True, default=None, verbose_name='威望')
    approve = IntegerField(null=True, default=None, verbose_name='赞同')
    thank = IntegerField(null=True, default=None, verbose_name='感谢')
    coins = IntegerField(null=True, default=None, verbose_name='金币')
    visits = IntegerField(null=True, verbose_name='访问量')
    prov = ForeignKeyField(Provs, null=True, related_name='users', verbose_name='省份')
    locate = CharField(null=True, verbose_name='地区')
    industry = CharField(null=True, verbose_name='行业')

    last_signin_at = DateTimeField(null=True, verbose_name='最后登录时间')
    crawled_at = DateTimeField(default=datetime.now, verbose_name='抓取时间')


class Posts(BaseModel):
    id = BigIntegerField(null=False, primary_key=True, verbose_name='id')
    title = CharField(max_length=255, verbose_name='帖子主题')
    content = TextField(null=True, verbose_name='帖子内容')
    user = ForeignKeyField(Users, null=False, related_name='posts', verbose_name='用户')
    views = IntegerField(null=True, verbose_name='浏览量')
    focus = IntegerField(null=True, verbose_name='关注数')

    last_actived_at = DateTimeField(null=True, verbose_name='最后活动时间')
    updated_at = DateTimeField(verbose_name='创建时间')
    crawled_at = DateTimeField(default=datetime.now, verbose_name='抓取时间')


class Replies(BaseModel):
    id = BigIntegerField(null=False, primary_key=True, verbose_name='id')
    post = ForeignKeyField(Posts, related_name='replies', verbose_name='主题')
    content = TextField(null=False, verbose_name='回复内容')
    user = ForeignKeyField(Users, related_name='replies', verbose_name='用户')

    updated_at = DateTimeField(verbose_name='创建时间')
    crawled_at = DateTimeField(default=datetime.now, verbose_name='抓取时间')


class Topics(BaseModel):
    id = BigIntegerField(null=False, primary_key=True, verbose_name='id')
    topic = CharField(max_length=255, unique=True, null=False, verbose_name='主题')


class TopicUser(BaseModel):
    user = ForeignKeyField(Users, related_name='topicuser', verbose_name='用户')
    topic = ForeignKeyField(Topics, related_name='topicuser', verbose_name='主题')
    approve = IntegerField(default=0, verbose_name='赞同')
    thank = IntegerField(default=0, verbose_name='感谢')

    class Meta:
        primary_key = CompositeKey('user', 'topic')


if __name__ == '__main__':
    try:
        Industry.create_table()
        Provs.create_table()
        Users.create_table()
        Posts.create_table()
        Replies.create_table()
        Topics.create_table()
        TopicUser.create_table()
        print('create table completed!')
    except Exception as err:
        print(err)

    try:
        user_lv_field = IntegerField(null=True, verbose_name='用户等级')
        user_industry_field = ForeignKeyField(Industry, null=True, related_name='users', to_field=Industry.id, verbose_name='行业')
        migrate(
            migrator.add_not_null('provs', 'prov'),
            migrator.drop_column('users', 'lv'),
            migrator.add_column('users', 'lv', user_lv_field),
            migrator.drop_column('users', 'industry'),
            migrator.add_column('users', 'industry', user_industry_field),
        )
        print('migration completed!')
    except Exception as err:
        print(err)
