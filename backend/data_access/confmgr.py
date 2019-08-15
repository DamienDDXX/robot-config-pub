#!/usr/bin/python
# -*- coding: utf8 -*-

import configparser
import os

base_dir = os.path.dirname(os.path.abspath(__file__))


def get_conf_section(section):
    conf = configparser.ConfigParser()
    conf_path = os.path.join(base_dir, 'data.ini')
    conf.read(conf_path)
    return conf[section], conf


def update_conf(conf):
    with open(os.path.join(base_dir, 'data.ini'), 'w') as config_file:
        conf.write(config_file)

