# -*- coding: utf-8 -*-

import os

database_server = os.environ['DATABASE_SERVER']
database_server_deals = os.environ['DATABASE_SERVER_DEALS']
database_server_main = os.environ['DATABASE_SERVER_MAIN']

API_SERVER = os.environ['API_SERVER']

AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']

SMTP_SERVER = os.environ['SMTP_SERVER']
SMTP_PORT = os.environ['SMTP_PORT']
SMTP_LOGIN = os.environ['SMTP_LOGIN']
SMTP_PASSWORD = os.environ['SMTP_PASSWORD']
SECRET_KEY = os.environ['SECRET_KEY']

FB_APP_ID = os.environ['FB_APP_ID']

fcm_key = os.environ['fcm_key']
PRODUCT_IMAGE_BUCKET_NAME = os.environ['PRODUCT_IMAGE_BUCKET_NAME']
NEW_PRODUCT_IMAGE_BUCKET = os.environ['NEW_PRODUCT_IMAGE_BUCKET']
STORE_IMAGE_BUCKET = os.environ['STORE_IMAGE_BUCKET']
S3_ENDPOINT = os.environ['S3_ENDPOINT']
S3_HOST = os.environ['S3_HOST']
DEALS_IMAGE_BUCKET = os.environ['DEALS_IMAGE_BUCKET']

opl_server = os.environ['opl_server']

SCANS_IMAGE_BUCKET = os.environ['SCANS_IMAGE_BUCKET']
PRODUCT_PICS_BUCKET = os.environ['PRODUCT_PICS_BUCKET']

prod_image_dir = 'products'

scan_points_frequency = 1

SAVINGS_MIN = 1.5
SAVINGS_MIN_PERCENT = 0.25
SAVINGS_MAX_PERCENT = 0.76
DEALS_MAX_AGE = 20

APP_VERSION_iOS = 326
APP_VERSION_ANDROID = 95

TOPSAVINGS_DEBUG = True
