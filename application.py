# -*- coding: utf-8 -*-
import pymysql

from sqlalchemy import or_, text, create_engine
from sqlalchemy.orm import sessionmaker

from flask import Flask, g, request, render_template, redirect, Response

from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth, MultiAuth
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import JSONWebSignatureSerializer as JWT

import requests
import simplejson as json

from settings import SECRET_KEY

from settings import database_server
from settings import database_server_deals
from settings import database_server_main

from time import strftime
import traceback

import os

import models


import logging
DEBUG = True
logging_level = logging.INFO
if DEBUG:
    logging_level = logging.DEBUG
logging.basicConfig(level=logging_level)

pymysql.install_as_MySQLdb()

engine = create_engine(database_server, encoding='utf-8', pool_recycle=600, pool_timeout = 20, pool_size=1000, max_overflow=300, pool_pre_ping=True)
engine_deals = create_engine(database_server_deals, encoding='utf-8', pool_recycle=600, pool_timeout = 20, pool_size=1000, max_overflow=300, pool_pre_ping=True)
engine_main = create_engine(database_server_main, encoding='utf-8', pool_recycle=600, pool_timeout = 20, pool_size=1000, max_overflow=300, pool_pre_ping=True)

Session = sessionmaker(bind=engine)
Session_deals = sessionmaker(bind=engine_deals)
Session_main = sessionmaker(bind=engine_main)

application = app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
jwt = JWT(app.config['SECRET_KEY'])

from src import authentication
from src import deals
from src import info
from src import logins
from src import notifications
from src import prices
from src import product
from src import scan
from src import search
from src import settings
from src import share
from src import shopping_list
from src import similar
from src import smart_products
from src import startup
from src import stores
from src import tabs


@app.route('/robots.txt', methods=['POST', 'GET'])
def api_robots_txt():
    return render_template('robots.txt')


@app.route('/', methods=['GET'])
@app.route('/load_balancer_check', methods=['GET'])
def api_home():
    # don't change this or load balancer will go down
    return Response('Download the TopSavings App for Great Deals on Groceries!', mimetype="application/json")


@app.before_request
def before_request():
    g.user_id = '0'


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(81), debug=True, threaded=True)