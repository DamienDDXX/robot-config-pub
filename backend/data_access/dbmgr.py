#!/usr/bin/python
# -*- coding: utf8 -*-

import configparser
import os
from mysql.connector import connect

db_config = configparser.ConfigParser()
base_dir = os.path.dirname(os.path.abspath(__file__))
db_config.read(os.path.join(base_dir, 'db.config'))

dbserver = db_config['DEFAULT']['dbserver']
user = db_config['DEFAULT']['user']
password = db_config['DEFAULT']['pwd']


def get_connection():
    conn = connect(host=dbserver, user=user, passwd=password)
    return conn
