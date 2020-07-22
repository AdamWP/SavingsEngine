# -*- coding: utf-8 -*-

from __main__ import app
from __main__ import Session
from __main__ import Session_main
from __main__ import g
from __main__ import Response
from __main__ import request
from __main__ import json

from src.authentication import multi_auth
from src.email import email_crash_report
from src.utils import get_user_ip
from src.utils import check_gps
from src.utils import record_api_activity

import sys
import os
import time
import datetime
import simplejson

import threading
import uuid

import requests

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from settings import SMTP_SERVER
from settings import SMTP_PORT
from settings import SMTP_LOGIN
from settings import SMTP_PASSWORD

from settings import opl_server

import models

import re

from decimal import Decimal

from settings import S3_ENDPOINT
from settings import STORE_IMAGE_BUCKET


@app.route('/v2/get_prices', methods=['POST'])
@multi_auth.login_required
def api_get_prices_v2():
    try:

        start = time.time()
        user_ipaddress = str(get_user_ip())

        try:
            submission = request.get_json()

        except Exception as e:
            print(e)
            email_crash_report('/v2/get_prices', e)
            result = '{"status": "MUST BE IN JSON FORMAT"}'
            print(str(datetime.datetime.now()) + ' IP:' + str(user_ipaddress) + ' user_id:' + str(g.user_id) + ' /v2/get_prices:' + ' ' + result)
            return Response(result, mimetype="application/json")

        if 'gps' in submission:
            gps = submission['gps']
            gps_info = check_gps(gps)
            if gps_info:
                gps_lat = gps_info['gps_lat']
                gps_lng = gps_info['gps_lng']
                gps = str(gps_lat) + ',' + str(gps_lng)
            else:

                result = '{"status": "GPS Error"}'
                print(str(datetime.datetime.now()) + ' IP:' + str(user_ipaddress) + ' user_id:' + str(g.user_id) + ' ' + result)
                return Response(result, mimetype="application/json")
        else:
            result = '{"status": "GPS Error"}'
            return Response(result, mimetype="application/json")

        if 'prod_id' in submission:
            prod_id = submission['prod_id']
            if prod_id is not None:
                prod_id = prod_id.strip()
            if prod_id is None or prod_id == '':
                result = '{"status": "prod_id cannot be null"}'
                print(str(datetime.datetime.now()) + ' IP:' + str(user_ipaddress) + ' user_id:' + str(g.user_id) + ' ' + result)
                return Response(result, mimetype="application/json")
        else:
            result = '{"status": "missing prod_id: string"}'
            print(str(datetime.datetime.now()) + ' IP:' + str(user_ipaddress) + ' user_id:' + str(g.user_id))
            return Response(result, mimetype="application/json")

        prod_id_list = []
        prod_id_list.append(prod_id)

        with requests.Session() as opl_session:

            payload ={}
            payload['gps_lat'] = gps_lat
            payload['gps_lng'] = gps_lng
            payload['prod_id_list'] = prod_id_list
            payload['user_id'] = g.user_id
            payload['ipaddress'] = str(get_user_ip())

        try:
            opl_result = opl_session.request('POST', opl_server, json=payload,  timeout=20)

        except Exception as e:
            print(e)

        # note = opl_result['note']
        note = None

        prices = {}
        prices['prod_id'] = prod_id

        all_prices = get_prices(prod_id, gps_lat, gps_lng, None)

        prices['prices'] = all_prices['prices']

        saving_price = all_prices['saving_price']
        best_price = all_prices['price']
        if best_price is None:
            best_price = 0

        if saving_price is None:
            saving_price = 0

        if saving_price > 0 and best_price > 0:
            save_ratio = saving_price / (saving_price + best_price)
            save_ratio = save_ratio * 100
            save_ratio = int(save_ratio)
        else:
            save_ratio = 0

        # add more options like multi, new, etc
        if 49 < save_ratio < 75:
            prices['crest_color'] = '#fa0000'
            prices['crest_text'] = str(save_ratio) + '% OFF'
            prices['promo_color'] = '#fa0000'
            prices['promo_text'] = str(save_ratio) + '% OFF'
        elif save_ratio > 24:
            prices['crest_color'] = '#fa7000'
            prices['crest_text'] = str(save_ratio) + '% OFF'
            prices['promo_color'] = '#fa7000'
            prices['promo_text'] = str(save_ratio) + '% OFF'

        elif saving_price > 1:
            saving_price_disp = '{0:.2f}'.format(saving_price)
            prices['crest_color'] = '#4cd96d'
            prices['crest_text'] = 'Save $' + str(saving_price_disp)
            prices['promo_color'] = '#4cd96d'
            prices['promo_text'] = 'Save $' + str(saving_price_disp)
        else:
            prices['crest_color'] = None
            prices['crest_text'] = None
            prices['promo_color'] = None
            prices['promo_text'] = None

        # prices['prices'] = price_list
        result = json.dumps(prices)

        end = time.time()

        execution_time = end - start
        p_api_act = threading.Thread(target=record_api_activity, args=(g.user_id, gps_lat, gps_lng, '/v2/get_prices', str(get_user_ip()), execution_time), kwargs={'prod_id': prod_id, 'note': note})
        p_api_act.start()

        print(str(datetime.datetime.now()) + ' IP:' + str(user_ipaddress) + ' user_id:' + str(g.user_id) + ' /v2/get_prices ')

        print('Execution time (/v2/get_prices): %s' % (end - start))
        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/v2/get_prices', error_message)
        return False


def get_prices(prod_id, gps_lat, gps_lng, current_store_id):
    try:
        start = time.time()

        session = Session()

        sql_query = 'select * from (select @rn := @rn + 1 AS rn, d1.* from (SELECT t1.post_time, t1.start, t1.price, (t1.price / t1.quantity) as base_price, t1.units, t1.quantity, stores.id, stores.short_name as store_name, stores.address, stores.logo, stores.chain, stores.gps_lat, stores.gps_lng, stores.online, (SELECT id FROM urls WHERE prod_id = "' + str(prod_id) + '" and chain = stores.chain ORDER BY id desc LIMIT 1) AS url_id, (select size from item_info where prod_id = "' + str(prod_id) + '" order by id desc limit 1) as size, (select units from item_info where prod_id = "' + str(prod_id) + '" order by id desc limit 1) as size_units, (select quantity from item_info where prod_id = "' + str(prod_id) + '" order by id desc limit 1) as size_quantity, (select quantity_units from item_info where prod_id = "' + str(prod_id) + '" order by id desc limit 1) as quantity_units, (select id from user_stores_disabled where user_id = "' + str(g.user_id) + '" and chain = stores.chain limit 1) as store_disabled_id, (select st_distance_sphere(stores.pt, Point(' + gps_lng + ', ' + gps_lat + '))) AS distance FROM stores, scans t1 INNER JOIN (SELECT Max(scan_id) max_id, store_id FROM scans WHERE prod_id = "' + str(prod_id) + '" AND price IS NOT NULL AND scans.expiry > now() GROUP BY store_id) t2 ON t1.scan_id = t2.max_id WHERE t1.store_id = stores.id AND (select st_distance_sphere(stores.pt, Point(' + gps_lng + ', ' + gps_lat + ')) <= ' + str(g.distance) + ' or stores.online = 1) ORDER BY price) d1 inner join (select min(distance) as min_dist, chain from (SELECT t1.post_time, t1.start, t1.price, stores.id, stores.logo, stores.chain, stores.gps_lat, stores.gps_lng, stores.online, (SELECT id FROM urls WHERE prod_id = "' + str(prod_id) + '" and chain = stores.chain ORDER BY id desc LIMIT 1) AS url_id, (select id from user_stores_disabled where user_id = "' + str(g.user_id) + '" and chain = stores.chain limit 1) as store_disabled_id, (select st_distance_sphere(stores.pt, Point(' + gps_lng + ', ' + gps_lat + '))) AS distance FROM stores, scans t1 INNER JOIN (SELECT Max(scan_id) max_id, store_id  FROM scans WHERE prod_id = "' + str(prod_id) + '" AND price IS NOT NULL AND scans.expiry > now() GROUP BY store_id) t2 ON t1.scan_id = t2.max_id WHERE t1.store_id = stores.id AND (select st_distance_sphere(stores.pt, Point(' + gps_lng + ', ' + gps_lat + ')) <= ' + str(g.distance) + ' or stores.online = 1) ORDER BY price) t3 group by chain, price) as d2 on d1.chain = d2.chain and d1.distance = d2.min_dist CROSS JOIN (SELECT @rn := 0) AS const order by base_price, price, distance, online desc)t1 order by base_price'

        item_info = session.execute(sql_query)
        session.close()

        prices_count = 0

        best_price_enabled = None
        saving_price_enabled = None
        omit_amazon = True

        prices = {}
        price_list = []

        high_base_price = None
        high_units = None

        if item_info:
            item_info = list(item_info)
            high_price = 0
            low_price = 0

            for row in item_info:
                base_price = row.base_price
                price = row.price
                price_quantity = row.quantity
                price = price / price_quantity
                if base_price > high_price:
                    high_base_price = base_price
                    high_price = price
                    high_units = row.units

                if price > 0 and low_price == 0:
                    low_price = price

            high_price = '{0:.2f}'.format(high_price)
            high_price = Decimal(high_price)

            was_price = high_price
            if high_units == 'lb':
                high_units = 'kg'

            post_was_price = high_units

            high_unit_price = high_base_price

            for row in item_info:

                if len(item_info) > 1 and item_info[-1]['chain'] == 'Amazon':
                    second_high_price = item_info[-2]['price']

                    if high_price > (second_high_price * 11 / 10):
                        high_price = second_high_price
                        high_price_quantity = item_info[-2]['quantity']
                        omit_amazon = True

                price_record = {}
                if row['price'] is None or row['price'] == '':
                    price_record['order'] = None
                    price_record['date_time'] = None
                    price_record['display_time'] = None
                    price_record['date'] = None
                    price_record['date_color'] = None
                    price_record['date_opacity'] = None

                    price_record['pre_price'] = None
                    price_record['currency'] = None
                    price_record['price'] = None
                    price_record['quantity'] = None
                    price_record['post_price'] = None
                    price_record['was_price'] = None
                    price_record['post_was_price'] = None
                    price_record['unit_price'] = None
                    price_record['units'] = None
                    price_record['post_unit_price'] = None

                    price_record['saving_price'] = None

                elif omit_amazon is not True or row['chain'] != 'Amazon':

                    if row['chain'] == 'Amazon':
                        price_record['order'] = None
                        price_record['date_time'] = None
                        price_record['display_time'] = None
                        price_record['date'] = None
                        price_record['date_color'] = None
                        price_record['date_opacity'] = None
                        # price_record['display_time'] = None

                        price_record['pre_price'] = None
                        price_record['currency'] = None
                        price_record['price'] = None
                        price_record['quantity'] = None
                        price_record['pre_price'] = None
                        price_record['post_price'] = None
                        price_record['was_price'] = None
                        price_record['post_was_price'] = None
                        price_record['unit_price'] = None
                        price_record['units'] = None
                        price_record['post_unit_price'] = None
                        price_record['saving_price'] = None

                    else:
                        post_time = row.post_time
                        start_time = row.start

                        if start_time is None:
                            start_time = post_time

                        start_time = start_time.replace(second=0, minute=0)

                        # start_time = start_time.dt.tz_localize('UTC').dt.tz_convert('America/New_York').astype(str)

                        disp_time = 'as of ' + str(start_time) + ' EST'

                        price_record['date'] = disp_time
                        price_record['date_time'] = disp_time
                        price_record['display_time'] = disp_time
                        price_record['date_color'] = '#000000'
                        price_record['date_opacity'] = 0.3

                        price = row['price']

                        size = row['size']
                        size_units = row['size_units']

                        quantity = row.quantity

                        if quantity is None or quantity == 1:
                            quantity = 1

                        size_quantity = row.size_quantity
                        if size_quantity is None or size_quantity == 1:
                            size_quantity = 1

                        quantity_units = row.quantity_units

                        if size_units is None:
                            size_units = ''
                        if size_units[-1:] == 's':
                            size_units = size_units[:-1]

                        if quantity_units is not None and quantity_units != '':
                            size_units = str(quantity_units)

                        unit_price_mult = ''
                        unit_price = None
                        units = None
                        unit_price_units = None

                        if size == '' or size is None:
                            size = '1'

                        if size is not None and size != '' and re.match(r'^-?\d+(\.\d+)?$', size):
                            size = Decimal(size)
                            unit_price = price / size
                            unit_price = unit_price / quantity
                            unit_price = unit_price / size_quantity

                        if high_unit_price is not None:
                            if high_unit_price < 0.009:
                                unit_price = unit_price * 100
                                unit_price_mult = '100'

                        if size_units is not None and size_units != '':
                            # units = str(unit_price_mult) + str(size_units)
                            unit_price_units = '/' + str(unit_price_mult) + ' ' + str(size_units)

                        if unit_price is not None:
                            unit_price = '{0:.4f}'.format(unit_price)
                            unit_price = Decimal(unit_price)

                        saving_price = (high_price - (price / quantity)) * quantity

                        price = '{0:.2f}'.format(price)
                        price = Decimal(price)

                        price_record['currency'] = '$'

                        price_record['quantity'] = quantity

                        if row['units'] is not None:
                            units = row['units']

                            if quantity > 1:
                                post_price = '/' + str(quantity) + str(units)
                                unit_price = price / quantity
                                unit_price = '{0:.4f}'.format(unit_price)
                                unit_price = Decimal(unit_price)
                                if units == 'lb':
                                    unit_price = unit_price / Decimal(0.453592)
                                    # was_price = was_price / Decimal(0.453592)
                                unit_price = '{0:.4f}'.format(unit_price)
                                units = 'kg'
                                unit_price_units = '/kg'
                            elif units == 'lb':
                                units = 'kg'
                                price = price / Decimal(0.453592)
                                price = '{0:.2f}'.format(price)
                                price = Decimal(price)
                                post_price = '/' + str(units)

                                # was_price = was_price / Decimal(0.453592)

                            else:
                                post_price = '/' + str(units)
                        else:
                            post_price = None

                        if quantity > 1 and units is None:
                            price_record['pre_price'] = str(quantity) + '/'
                        else:
                            price_record['pre_price'] = None

                        price_record['price'] = price
                        price_record['post_price'] = post_price

                        price_record['was_price'] = was_price
                        price_record['post_was_price'] = post_was_price

                        # todo temp fix. Dec 16, 2019 app shows no price is unit price is null
                        if unit_price is None:
                            unit_price = price
                            unit_price_units = post_price
                        price_record['unit_price'] = unit_price
                        price_record['units'] = units
                        price_record['post_unit_price'] = unit_price_units

                        if saving_price > 0:
                            saving_price = '{0:.2f}'.format(saving_price)
                            saving_price = Decimal(saving_price)
                            price_record['saving_price'] = saving_price
                        else:
                            price_record['saving_price'] = None

                        if (saving_price_enabled is None or saving_price_enabled < saving_price) and row['store_disabled_id'] is None:
                            best_price_enabled = price
                            saving_price_enabled = saving_price

                if row['id'] is None or row['id'] == '':
                    store_id = 0
                    price_record['store_id'] = None
                else:
                    store_id = row['id']
                    price_record['store_id'] = str(row['id'])

                if row['address'] is None or row['address'] == '':
                    store_address = None
                else:
                    store_address = row['store_name']
                    if store_address is None:
                        store_address = row['address']

                    if store_address == 'Amazon':
                        store_address = 'Online Delivery'

                if store_id == 1:
                    price_record['info'] = 'Product prices and available are accurate as of the date/time indicated and are subject to change. Any price and available information displayed on Amazon.ca at the time of purchase will apply to the purchase of this product.'
                else:
                    price_record['info'] = 'Some prices are crowd sourced. We strive for accuracy however prices may fluctuate. TopSavings is not responsible for innacuracies. Please contact us if you find a problem.'

                if row['chain'] is None or row['chain'] == '':
                    price_record['store_name'] = None
                else:
                    price_record['store_name'] = str(row['chain'])

                if row['logo'] is None or row['logo'] == '':
                    price_record['store_image'] = None
                    price_record['store_logo'] = None
                    price_record['store_thumb'] = None
                else:

                    price_record[
                        'store_image'] = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/stores/' + str(row['logo'])

                    price_record['store_logo'] = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/stores/' + str(row['logo'])

                    price_record['store_thumb'] = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/stores_sm/' + str(row['logo'])

                if row['distance'] is None or row['distance'] == '':
                    price_record['store_dist'] = None
                else:
                    store_distance = row['distance']

                    store_distance = store_distance / 1000
                    store_distance = round(store_distance, 1)

                    if store_distance == 1.0:
                        store_distance = 1
                    elif store_distance < 0.1:
                        store_distance = 0

                    # todo shouldn't be hard coded
                    if row['id'] < 100:
                        store_distance = 0

                    price_record['store_dist'] = store_distance

                if row['gps_lat'] is None or row['gps_lat'] == '':
                    price_record['store_lat'] = None
                else:
                    price_record['store_lat'] = str(row['gps_lat'])

                if row['gps_lng'] is None or row['gps_lng'] == '':
                    price_record['store_lng'] = None
                else:
                    price_record['store_lng'] = str(row['gps_lng'])

                # if row['url_id'] is None or row['url_id'] == '' or row['online'] != 1:
                if row['url_id'] is None or row['url_id'] == '':
                    price_record['url'] = None
                    available_at = store_address
                    available_icon = None
                    available_color = '#000000'
                else:
                    price_record['url'] = 'https://www.TopSavings.com/click?u=' + str(
                        g.user_id) + '&i=' + str(row['url_id'])

                    available_color = '#0176FF'

                    if store_address is None:
                        store_address = 'Online'
                        available_at = 'Online Delivery'
                        available_icon = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/delivery@3x.png'
                    else:
                        available_at = store_address + ' Online Pickup'
                        available_icon = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/pickup@3x.png'

                price_record['store_address'] = store_address
                price_record['available_at'] = available_at
                price_record['available_color'] = available_color
                price_record['available_icon'] = available_icon

                if omit_amazon is not True or row['chain'] != 'Amazon':
                    prices_count = prices_count + 1
                    if prices_count > 0:
                        price_list.append(price_record)

                if row['chain'] == 'Amazon':
                    price_record['open_in_app'] = False
                else:
                    price_record['open_in_app'] = True

                if prices_count == 1:
                    str_sql = 'select * from urls where chain = "Amazon" and prod_id = "' + prod_id + '" order by id desc limit 1'

                    amazon_url_info = session.execute(str_sql)
                    session.close()

                    amazon_url_info = list(amazon_url_info)

                    for row in amazon_url_info:
                        if row.url is not None and row.url != '':
                            price_record = {}
                            url_id = row.id
                            price_record['date_time'] = None
                            price_record['display_time'] = None
                            price_record['currency'] = None
                            price_record['price'] = None
                            price_record['quantity'] = None
                            price_record['saving_price'] = None
                            price_record['store_id'] = '1'
                            price_record['store_address'] = 'Delivery'
                            price_record['store_name'] = 'Amazon'
                            price_record['store_image'] = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/stores/amazon@3x.png'

                            price_record['store_logo'] = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/stores/amazon@3x.png'

                            price_record['store_thumb'] = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/stores_sm/amazon@3x.png'
                            price_record['store_lat'] = '0'
                            price_record['store_lng'] = '0'
                            price_record['url'] = 'https://www.TopSavings.com/click?u=' + str(g.user_id) + '&i=' + str(url_id)
                            price_record['open_in_app'] = False
                            price_list.append(price_record)

                            prices_count = prices_count + 1

        else:
            price_record = {}
            price_record['order'] = None
            price_record['date_time'] = None
            price_record['display_time'] = None
            price_record['date'] = None
            price_record['date_color'] = None
            price_record['date_opacity'] = None

            price_record['pre_price'] = None
            price_record['currency'] = None
            price_record['price'] = None
            price_record['quantity'] = None
            price_record['post_price'] = None
            price_record['was_price'] = None
            price_record['post_was_price'] = None
            price_record['unit_price'] = None
            price_record['units'] = None
            price_record['post_unit_price'] = None

            price_record['saving_price'] = None

            price_list.append(price_record)

        prices['prices'] = price_list

        prices['price'] = best_price_enabled
        prices['saving_price'] = saving_price_enabled
        # result = json.dumps(prices)
        end = time.time()
        execution_time = end - start
        print('Execution time (get_prices): ' + str(execution_time))

        return prices

    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('get_prices', error_message)

    return {'prices': []}


def get_best_price(user_id, distance, gps_lat, gps_lng, prod_id, current_store_id, size, units):

    try:
        start = time.time()
        session = Session()
        prod_id = str(prod_id)

        sql_query = 'select d1.* from (SELECT t1.post_time, t1.price, (t1.price / t1.quantity) as base_price, t1.units, t1.quantity, stores.id, stores.address, stores.logo, stores.chain, stores.gps_lat, stores.gps_lng, stores.online, (SELECT id FROM urls WHERE prod_id = "' + str(prod_id) + '" and chain = stores.chain ORDER BY id desc LIMIT 1) AS url_id, (select size from item_info where prod_id = "' + str(prod_id) + '" order by id desc limit 1) as size, (select units from item_info where prod_id = "' + str(prod_id) + '"  order by id desc limit 1) as size_units, (select quantity from item_info where prod_id = "' + str(prod_id) + '" order by id desc limit 1) as size_quantity, (select quantity_units from item_info where prod_id = "' + str(prod_id) + '" order by id desc limit 1) as quantity_units, (select id from user_stores_disabled where user_id = "' + str(user_id) + '" and chain = stores.chain limit 1) as store_disabled_id, (select st_distance_sphere(stores.pt, Point(' + gps_lng + ', ' + gps_lat + '))) AS distance FROM stores, scans t1 INNER JOIN (SELECT Max(scan_id) max_id, store_id FROM scans WHERE prod_id = "' + str(prod_id) + '" AND price IS NOT NULL AND scans.expiry > now() GROUP BY store_id) t2 ON t1.scan_id = t2.max_id WHERE t1.store_id = stores.id AND (select st_distance_sphere(stores.pt, Point(' + gps_lng + ', ' + gps_lat + ')) <= ' + str(distance) + ' or stores.online = 1) ORDER BY price) d1 inner join (select min(distance) as min_dist, chain from (SELECT t1.post_time, t1.price, stores.id, stores.logo, stores.chain, stores.gps_lat, stores.gps_lng, stores.online, (SELECT id FROM urls WHERE prod_id = "' + str(prod_id) + '" and chain = stores.chain ORDER BY id desc LIMIT 1) AS url_id, (select id from user_stores_disabled where user_id = "' + str(user_id) + '" and chain = stores.chain limit 1) as store_disabled_id, (select st_distance_sphere(stores.pt, Point(' + gps_lng + ', ' + gps_lat + '))) AS distance FROM stores, scans t1 INNER JOIN (SELECT Max(scan_id) max_id, store_id  FROM scans WHERE prod_id = "' + str(prod_id) + '" AND price IS NOT NULL AND scans.expiry > now()  GROUP BY store_id) t2 ON t1.scan_id = t2.max_id WHERE t1.store_id = stores.id AND (((select st_distance_sphere(stores.pt, Point(' + gps_lng + ', ' + gps_lat + '))) <= ((SELECT user.distance FROM user WHERE id = ' + str(user_id) + ') * 1000)) or stores.online = 1) ORDER BY price) t3 group by chain, price) as d2 on d1.chain = d2.chain and d1.distance = d2.min_dist order by base_price, price, online desc, distance'

        item_info = session.execute(sql_query)
        session.close()

        best_post_time = None
        best_price = ''
        best_store_logo = ''
        best_store_id = ''
        best_store_address = ''
        best_store_gps_lat = None
        best_store_gps_lng = None

        best_store_name = ''
        best_store_distance = ''

        unit_price = ''
        saving_price = 0
        url_id = None

        item_info = list(item_info)

        for row in item_info:
            high_price = item_info[-1]['price']
            high_price_quantity = item_info[-1]['quantity']
            high_price = high_price / high_price_quantity

            if len(item_info) > 1 and item_info[-1]['chain'] == 'Amazon':
                second_high_price = item_info[-2]['price']
                second_high_price_quantity = item_info[-2]['quantity']
                second_high_price = second_high_price / second_high_price_quantity

                if high_price > (second_high_price * 11 / 10):
                    high_price = second_high_price
                    omit_amazon = True

            best_price = item_info[0]['price']
            best_price_quantity = item_info[0]['quantity']
            best_price = best_price / best_price_quantity

            best_price = round(best_price, 2)
            best_store_id = item_info[0]['id']

            unit_price = None

            best_post_time = item_info[0].post_time
            best_store_logo = item_info[0]['logo']
            best_store_name = item_info[0]['chain']
            best_store_chain = item_info[0]['chain']
            best_store_address = item_info[0]['address']
            best_store_gps_lat = item_info[0]['gps_lat']
            best_store_gps_lng = item_info[0]['gps_lng']
            best_store_distance = item_info[0]['distance']
            url_id = item_info[0]['url_id']

            best_store_distance = round(best_store_distance, 1)

            if best_store_id < 100:
                best_store_distance = None

            saving_price = high_price - best_price

        if saving_price > 0:
            saving_price = '{0:.2f}'.format(saving_price)

        else:
            saving_price = None

        if best_price == '' or best_price is None:
            # FIX TODO  handle items with no known prices in geographic range

            best_price = None
            saving_price = None

        end = time.time()

        print('Execution time (get_best_price): %s' % (end - start))

        return {'best_post_time': best_post_time, 'best_price': best_price, 'unit_price': unit_price,
                'best_store_id': best_store_id, 'best_store_logo': best_store_logo,
                'best_store_gps_lat': best_store_gps_lat, 'best_store_gps_lng': best_store_gps_lng,
                'best_store_distance': best_store_distance, 'saving_price': saving_price,
                'best_store_name': best_store_name, 'best_store_address': best_store_address,
                'best_store_chain': best_store_name, 'best_store_url_id': url_id}
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('get_best_price', error_message)
        return False


# todo should get screen shot when user reports
@app.route('/v2/report_price', methods=['POST'])
@app.route('/report_price', methods=['POST'])
@multi_auth.login_required
def api_report_price():
    try:
        start = time.time()
        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' /report_price:')


        try:
            submission = request.get_json()

        except Exception as e:
            print(e)
            email_crash_report('/report_price', e)
            result = '{"status": "MUST BE IN JSON FORMAT"}'
            return Response(result, mimetype="application/json")

        if 'gps' in submission:
            gps = submission['gps']
            gps_info = check_gps(gps)
            if gps_info:
                gps_lat = gps_info['gps_lat']
                gps_lng = gps_info['gps_lng']
            else:

                result = '{"status": "GPS Error"}'
                print(str(datetime.datetime.now()) + ' IP:' + str(user_ipaddress) + ' user_id:' + str(g.user_id) + ' ' + result)
                return Response(result, mimetype="application/json")
        else:
            result = '{"status": "GPS Error"}'
            return Response(result, mimetype="application/json")

        if 'prod_id' in submission:
            prod_id = submission['prod_id']
            if prod_id is not None:
                prod_id = prod_id.strip()
            if prod_id is None or prod_id == '':
                result = '["prod_id invalid"]'
                return Response(result, mimetype="application/json")
            else:
                session = Session()
                prod_info = session.query(models.item_info).filter(
                    (models.item_info.prod_id == prod_id)
                ).distinct().first()
                session.close()

                prod_name = prod_info.prod_name
        else:
            result = '{"status": "missing prod_id: string, null"}'
            return Response(result, mimetype="application/json")

        if 'store_id' in submission:
            store_id = submission['store_id']
            if store_id is not None:
                store_id = store_id.strip()
            if store_id == '':
                store_id = None

        else:
            result = '{"status": "missing store_id: string, null"}'
            return Response(result, mimetype="application/json")

        if 'price' in submission:
            price = submission['price']
            if price is not None:
                price = price.strip()
            if price == '':
                price = None
        else:
            result = '{"status": "missing price: string, null"}'
            return Response(result, mimetype="application/json")

        # submit to database

        submission = models.price_reports(
            prod_id=prod_id,
            user_id=int(g.user_id),
            gps_lat=gps_lat,
            gps_lng=gps_lng,
            store_id=store_id,
            price=price,
            post_time=datetime.datetime.utcnow(),
            ipaddress=str(get_user_ip())

        )
        session_main = Session_main()
        session_main.add(submission)
        session_main.commit()
        report_id = submission.id
        session_main.close()

        output_record = {}
        if report_id is not None:
            output_record['report_id'] = report_id
        else:
            output_record['report_id'] = 'Error'

        result = json.dumps(output_record)

        if price is None:
            price = ''

        if store_id is None:
            store_id = ''

        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'TopSavings Report'
        msg['From'] = 'TopSavings <mailer@TopSavings.com>'
        msg['To'] = 'TopSavings Reports'

        # text = "A product image has been submitted...."
        html = """\
                <html>
                  <head></head>
                  <body>
                    A report has been submitted.<BR><BR> Product: """ + prod_name + """<BR>Price: """ + price + """<BR>Store ID: """ + store_id + """<BR>USer ID: """ + str(g.user_id) + """<BR>

                  </body>
                </html>
                """

        # part1 = MIMEText(text, 'plain')
        part2 = MIMEText(html, 'html')

        # msg.attach(part1)
        msg.attach(part2)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.ehlo()
        server.starttls()
        server.login(SMTP_LOGIN, SMTP_PASSWORD)

        server.sendmail("mailer@TopSavings.com", "adam@topsavings.com", msg.as_string())
        server.sendmail("mailer@TopSavings.com", "steve@topsavings.com", msg.as_string())
        server.quit()

        end = time.time()

        execution_time = end - start
        p_api_act = threading.Thread(target=record_api_activity, args=(
            g.user_id, gps_lat, gps_lng, '/report_price', str(get_user_ip()), execution_time), kwargs={'user_activity': 1})
        p_api_act.start()

        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' /report_price')
        print('Execution time (/report_price): %s' % (end - start))

        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/report_price', error_message)
        return False
