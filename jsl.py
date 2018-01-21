# !/usr/bin/env python
# -*- coding: utf-8 -*-

from pyquery import PyQuery as pq



from logbook import Logger, StreamHandler, RotatingFileHandler
import sys
log_format = '[{record.time:%Y-%m-%d %H:%M:%S}] {record.level_name}::{record.channel}[{record.module}]:{record.lineno} - {record.message}'

StreamHandler(sys.stdout, format_string=log_format, level='DEBUG').push_application()
RotatingFileHandler('jsl.log', format_string=log_format, max_size=4096, backup_count=5, bubble=True).push_application()

log = Logger(__file__)
