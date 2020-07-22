# -*- coding: utf-8 -*-
from __main__ import app
from __main__ import Session
from __main__ import g
from __main__ import Response
from __main__ import request
from __main__ import json

import sys
import os
import time
import datetime
import threading
import random
import re
import unidecode


from src.authentication import multi_auth
from src.email import email_crash_report
from src.utils import get_user_ip
from src.utils import check_gps
from src.utils import record_api_activity

from src.stores import get_current_store
from src.prices import get_prices

from src.search import dm

from settings import S3_ENDPOINT
from settings import PRODUCT_IMAGE_BUCKET_NAME
from settings import STORE_IMAGE_BUCKET


@app.route('/v2/get_best_generic', methods=['POST'])
@multi_auth.login_required
def api_get_best_generic():
    try:
        start = time.time()
        session = Session()

        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' /v2/get_best_generic:')
        try:
            submission = request.get_json()
        except Exception as e:
            print(e)
            email_crash_report('/get_best_generic', e)

            result = '{"status": "MUST BE IN JSON FORMAT"}'
            print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' ' + result)
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
                return Response(result, mimetype="application/json")
        else:
            result = '{"status": "GPS Error"}'
            return Response(result, mimetype="application/json")

        if 'generic_name' in submission:
            generic_name = submission['generic_name']

        else:
            result = '{"status": "missing generic_name: string"}'
            return Response(result, mimetype="application/json")

        sql_query = 'select item_info.prod_id, item_info.brand, item_info.prod_name, item_info.image, item_info.size, item_info.units,  item_info.quantity AS size_quantity, item_info.quantity_units, item_info.awaiting_approval, scans.quantity, scans.unit_price, St_distance_sphere(stores.pt, Point(' + str(gps_lng) + ',' + str(gps_lat) + ')) as distance from (select * from search_tags where search_tags.tag = "' + str(generic_name) + '")t1  left join item_info on item_info.prod_id = t1.prod_id inner join scans on item_info.prod_id = scans.prod_id and scans.expiry > now() and (scans.start <= now() or scans.start is null) and scans.price is not null left join stores on scans.store_id = stores.id where not exists (select id from user_stores_disabled where user_id = "' + str(g.user_id) + '" and chain = stores.chain) and (St_distance_sphere(stores.pt, Point(' + str(gps_lng) + ',' + str(gps_lat) + ')) <= ' + str(g.distance) + ') order by -unit_price desc limit 1'

        item_info = session.execute(sql_query)
        session.close()

        item_record = {}
        for row in item_info:

            if row.prod_id is None:
                item_record['prod_id'] = None
                prod_id = None
            else:
                item_record['prod_id'] = str(row.prod_id)
                prod_id = str(row.prod_id)

            if prod_id is None:
                item_record['image'] = None
                item_record['image_thumb'] = None

            elif row.image is None:
                item_record['image'] = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/no_image_grocery_lg.png'
                item_record['image_thumb'] = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/no_image_grocery_sm.png'
            elif row.awaiting_approval is not None:
                item_record['image'] = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME + '/sm_new/' + str(row.image)
                item_record['image_thumb'] = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME + '/sm_new/' + str(row.image)
            else:
                item_record['image'] = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME + '/sm_new/' + str(row.image)
                item_record['image_thumb'] = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME  + '/sm_new/' + str(row.image)

            # todo update nutrition
            item_record['nutr_score'] = None
            item_record['nutr_info'] = None

            if row.size is None:
                size = None
            else:
                size = str(row.size)

                if row.units is not None:
                    size = size + ' ' + str(row.units)

                if row.size_quantity is not None and row.quantity_units is None:
                    size_quantity = row.size_quantity

                    size = str(size_quantity) + ' X ' + str(size)

            if row.prod_name is None:

                item_record['prod_name'] = None
            else:
                prod_name = row.prod_name
                prod_name = str(prod_name)

                brand = row.brand

                if brand is not None and brand != '':
                    if brand not in prod_name:
                        prod_name = brand + ' ' + prod_name

                if size is not None:
                    prod_name = prod_name + ' ' + size

                item_record['prod_name'] = prod_name

            item_record['size'] = size

            if row.quantity is None:
                item_record['quantity'] = 1
                quantity = 1
            else:
                item_record['quantity'] = row.quantity
                quantity = row.quantity

            if prod_id is not None and prod_id != '':
                all_prices = get_prices(prod_id, gps_lat, gps_lng, None)
                prices = all_prices['prices']

            else:
                prices = None

            item_record['prices'] = prices

            if prices is None:

                item_record['store_id'] = None
                item_record['url'] = None
                item_record['store'] = None
                item_record['store_image'] = None
                item_record['store_logo'] = None
                item_record['store_thumb'] = None
                item_record['store_name'] = None
                item_record['store_address'] = None
                item_record['currency'] = None
                item_record['price'] = None
                item_record['saving_price'] = None
                item_record['date_time'] = None

            elif len(prices) > 0:
                best_store_name = prices[0]['store_name']
                if best_store_name != 'Amazon':
                    item_record['store_id'] = prices[0]['store_id']
                    item_record['url'] = prices[0]['url']

                    item_record['store_image'] = prices[0]['store_image']
                    item_record['store_logo'] = prices[0]['store_image']
                    item_record['store_thumb'] = prices[0]['store_thumb']
                    item_record['store_name'] = prices[0]['store_name']
                    item_record['store_address'] = prices[0]['store_address']

                    price = prices[0]['price']
                    if price is not None:

                        item_record['currency'] = '$'
                        item_record['price'] = price
                    else:
                        item_record['currency'] = None
                        item_record['price'] = None

                    saving_price =  prices[0]['saving_price']
                    if saving_price is not None:

                        item_record['saving_price'] = saving_price
                    else:
                        item_record['saving_price'] = None
                elif len(prices) > 1:
                    item_record['store_id'] = prices[1]['store_id']
                    item_record['url'] = prices[1]['url']
                    item_record['store_image'] = prices[1]['store_image']
                    item_record['store_logo'] = prices[1]['store_image']
                    item_record['store_thumb'] = prices[1]['store_thumb']
                    item_record['store_name'] = prices[1]['store_name']
                    item_record['store_address'] = prices[1]['store_address']
                    price = prices[0]['price']
                    if price is not None:
                        item_record['currency'] = '$'
                        item_record['price'] = price
                    else:
                        item_record['currency'] = None
                        item_record['price'] = None

                    saving_price = prices[0]['saving_price']

                    item_record['saving_price'] = saving_price

                    item_record['date_time'] = prices[1]['date_time']
                else:
                    item_record['store_id'] = None
                    item_record['url'] = None
                    item_record['store'] = None
                    item_record['store_image'] = None
                    item_record['store_logo'] = None
                    item_record['store_thumb'] = None
                    item_record['store_name'] = None
                    item_record['store_address'] = None
                    item_record['currency'] = None
                    item_record['price'] = None
                    item_record['saving_price'] = None
                    item_record['date_time'] = None

            else:
                item_record['store_id'] = None
                item_record['url'] = None
                item_record['store'] = None
                item_record['store_image'] = None
                item_record['store_logo'] = None
                item_record['store_thumb'] = None
                item_record['store_name'] = None
                item_record['store_address'] = None
                item_record['currency'] = None
                item_record['price'] = None
                item_record['saving_price'] = None
                item_record['date_time'] = None

        result = json.dumps(item_record)

        session.close()

        end = time.time()
        execution_time = end - start

        p_api_act = threading.Thread(target=record_api_activity, args=(g.user_id, gps_lat, gps_lng, '/v2/get_best_generic', str(get_user_ip()), execution_time), kwargs={'generic_name': generic_name})
        p_api_act.start()

        print('Execution time (/v2/get_best_generic): %s' % (end - start))
        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/v2/get_best_generic ' + str(generic_name) , error_message)
        return False


@app.route('/v2/get_generic_description', methods=['POST'])
@multi_auth.login_required
def api_get_generic_description():
    # if 1 == 1:
    try:
        start = time.time()

        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' /v2/get_generic_description:')
        try:
            submission = request.get_json()
        except Exception as e:
            print(e)
            email_crash_report('/v2/get_generic_description', e)
            result = '{"status": "MUST BE IN JSON FORMAT"}'
            print(
                str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' ' + result)
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
                return Response(result, mimetype="application/json")
        else:
            result = '{"status": "GPS Error"}'
            return Response(result, mimetype="application/json")

        if 'generic_name' in submission:
            generic_name = submission['generic_name']
        else:
            result = '{"status": "missing generic_name: string"}'
            return Response(result, mimetype="application/json")

        item_record = {}
        item_record['description'] = 'add to list -->'
        item_record['colour'] = '#7e7e73'

        result = json.dumps(item_record)

        end = time.time()
        execution_time = end - start

        p_api_act = threading.Thread(target=record_api_activity, args=(g.user_id, gps_lat, gps_lng, '/v2/get_generic_description', str(get_user_ip()), execution_time), kwargs={'generic_name': generic_name})
        p_api_act.start()

        print('Execution time (/v2/get_generic_description): %s' % (end - start))
        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/v2/get_generic_description', error_message)
        return False


@app.route('/v2/smart_products', methods=['POST'])
@multi_auth.login_required
def api_smart_products():

    try:
        start = time.time()
        session = Session()

        try:
            submission = request.get_json()
        except Exception as e:
            print(e)
            email_crash_report('/v2/smart_products', e)
            result = '{"status": "MUST BE IN JSON FORMAT"}'
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
                return Response(result, mimetype="application/json")
        else:
            result = '{"status": "GPS Error"}'
            return Response(result, mimetype="application/json")

        sql_list = 'select * from shopping_list_generic where rank is not null order by rank limit 100'

        item_info = session.execute(sql_list)
        item_info = list(item_info)
        session.close()

        generic_list = []

        for row in item_info:

            list_record = {}

            if row.name != '' and row.name is not None:
                generic_name = str(row.name)
                list_record['name'] = generic_name

                list_record['icon'] = 'https://www.topsavings.com/static/shopping_list_icons/' + str(row.icon)
                list_record['icon_light'] = 'https://www.topsavings.com/static/smart_icons_light/' + str(row.icon)
                list_record['bg_colour'] = '#B1B1B110'

                generic_list.append(list_record)

        suggested_list = {}

        suggested_list['title'] = 'Add Smart Products'

        suggested_list['text'] = 'By comparing brands and sizes, the product with the lowest unit price is found at a store near you.'

        suggested_list['image'] = 'https://www.topsavings.com/appimages/smart_products.png'

        suggested_list['info_id'] = 'smart products'

        suggested_list['smart_products'] = generic_list

        result = json.dumps(suggested_list)

        session.close()

        end = time.time()

        execution_time = end - start
        p_api_act = threading.Thread(target=record_api_activity, args=(g.user_id, gps_lat, gps_lng, '/v2/smart_products', str(get_user_ip()), execution_time))
        p_api_act.start()

        print('Execution time (/v2/smart_products): %s' % (end - start))

        return Response(result, mimetype="application/json")

    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/v2/smart_products', error_message)
        return False
