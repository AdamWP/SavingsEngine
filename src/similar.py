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


from src.authentication import multi_auth
from src.email import email_crash_report
from src.utils import get_user_ip
from src.utils import check_gps
from src.utils import record_api_activity

from src.stores import get_current_store
from src.prices import get_prices

from settings import S3_ENDPOINT
from settings import PRODUCT_IMAGE_BUCKET_NAME
from settings import STORE_IMAGE_BUCKET


@app.route('/get_similar', methods=['POST'])
@multi_auth.login_required
def api_get_similar():
    try:
        start = time.time()
        session = Session()
        output = {}
        items_list_json = []

        try:
            submission = request.get_json()

        except Exception as e:
            print(e)
            email_crash_report('/get_similar', e)

            result = '{"status": "MUST BE IN JSON FORMAT"}'
            print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(
                g.user_id) + ' /get_similar:' + ' ' + result)
            return Response(result, mimetype="application/json")

        if 'gps' in submission:
            gps = submission['gps']
            gps_info = check_gps(gps)
            if gps_info:
                gps_lat = gps_info['gps_lat']
                gps_lng = gps_info['gps_lng']
            else:
                result = '{"status": "GPS Error"}'
                return Response(result, mimetype="application/json")
        else:
            result = '{"status": "GPS Error"}'
            return Response(result, mimetype="application/json")

        if 'prod_id' in submission:
            prod_id = submission['prod_id']
            if prod_id is None:
                result = '{}'
                print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' ' + result)
                return Response(result, mimetype="application/json")
        else:
            result = '{"status": "missing prod_id: string"}'
            print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' ' + result)
            return Response(result, mimetype="application/json")

        sql_query = 'select distinct item_info.*, (select image from images where prod_id = item_info.prod_id order by id limit 1) as image, (select quantity from shopping_list where user_id = "' + str(g.user_id) + '" and prod_id = item_info.prod_id order by id limit 1) as quantity from item_info, scans where sub_category2 = (select sub_category2 from item_info where prod_id = "' + prod_id + '" limit 1) and scans.prod_id = item_info.prod_id and scans.price is not null and scans.expiry > now() and item_info.prod_id != "' + prod_id + '" order by scans.price limit 5'

        item_info = session.execute(sql_query)

        item_info = list(item_info)
        session.close()
        prod_id_list = []
        for row in item_info:
            if row.prod_id != '' and row.prod_id is not None:
                prod_id_list.append(row.prod_id)

        item_num = 0
        for row in item_info:

            if item_num < 50:
                item_num = item_num + 1
                list_item_info = {}
                if row.prod_id is None:
                    list_item_info['prod_id'] = None
                else:
                    list_item_info['prod_id'] = str(row.prod_id)
                if row.prod_name is None:

                    list_item_info['prod_name'] = None
                else:
                    # list_item_info['name'] = unicode(row.prod_name, errors='ignore')
                    prod_name = row.prod_name

                    brand = row.brand

                    if brand is not None and brand != '':
                        if brand not in prod_name:
                            prod_name = brand + ' ' + prod_name

                    list_item_info['prod_name'] = prod_name

                if row.image is None:
                    list_item_info['image'] = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/no_image_grocery_lg.png'
                    list_item_info['image_thumb'] = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/no_image_grocery_sm.png'
                else:
                    if row.awaiting_approval is None:
                        list_item_info['image'] = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME + '/sm_new/' + str(row.image)
                        list_item_info['image_thumb'] = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME + '/sm_new/' + str(row.image)
                    else:
                        list_item_info['image'] = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME + '/sm_new/' + str(row.image)
                        list_item_info['image_thumb'] = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME + '/sm_new/' + str(row.image)

                if row.quantity is None:
                    list_item_info['is_in_shopping_list'] = False
                else:
                    list_item_info['is_in_shopping_list'] = True

                # todo update nutrition

                list_item_info['nutr_score'] = None
                list_item_info['nutr_info'] = None

                if row.size is None:
                    size = None
                else:
                    size = str(row.size)

                if row.units is None:
                    list_item_info['size'] = size
                    units = None
                else:
                    units = str(row.units)
                    list_item_info['size'] = size + ' ' + str(row.units)

                all_prices = get_prices(prod_id, gps_lat, gps_lng, None)
                prices = all_prices['prices']

                list_item_info['prices'] = prices

                items_list_json.append(list_item_info)

        output['products'] = items_list_json

        result = json.dumps(output)

        session.close()

        end = time.time()

        execution_time = end - start
        p_api_act = threading.Thread(target=record_api_activity, args=(
            g.user_id, gps_lat, gps_lng, 'get_similar', str(get_user_ip()), execution_time),
                                     kwargs={'prod_id': prod_id})
        p_api_act.start()

        print('Execution time (/get_similar): %s' % (end - start))
        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/get_similar', error_message)
        return False


@app.route('/v2/get_similar', methods=['POST'])
@multi_auth.login_required
def api_get_similar_v2():
    try:
        start = time.time()
        session = Session()
        output = {}
        items_list_json = []

        try:
            submission = request.get_json()
        except Exception as e:
            print(e)
            email_crash_report('/v2/get_similar', e)

            result = '{"status": "MUST BE IN JSON FORMAT"}'
            print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' /v2/get_similar:' + ' ' + result)
            return Response(result, mimetype="application/json")

        if 'gps' in submission:
            gps = submission['gps']
            gps_info = check_gps(gps)
            if gps_info:
                gps_lat = gps_info['gps_lat']
                gps_lng = gps_info['gps_lng']
            else:
                result = '{"status": "GPS Error"}'
                return Response(result, mimetype="application/json")
        else:
            result = '{"status": "GPS Error"}'
            return Response(result, mimetype="application/json")

        if 'prod_id' in submission:
            prod_id = submission['prod_id']
            if prod_id is None:
                result = '{}'
                #print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' ' + result)
                #return Response(result, mimetype="application/json")
        else:
            result = '{"status": "missing prod_id: string"}'
            print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' ' + result)
            return Response(result, mimetype="application/json")

        if 'generic_name' in submission:
            generic_name = submission['generic_name']

        else:
            generic_name = None

        if generic_name is not None and generic_name != '':
            print('SIMILAR GENERIC A')
            sql_query = 'select distinct item_info.*,(SELECT id FROM shopping_list WHERE user_id = ' + str(g.user_id) + ' AND prod_id = t1.prod_id LIMIT 1) AS is_in_list from (select * from search_tags where tag = "' + str(generic_name) + '")t1 left join item_info on item_info.prod_id = t1.prod_id inner join scans on item_info.prod_id = scans.prod_id left join stores on scans.store_id = stores.id and scans.unit_price is not null and not exists (select id from user_stores_disabled where user_id = ' + str(g.user_id) + ' and chain = stores.chain) and (St_distance_sphere(stores.pt, Point(' + str(gps_lng) + ', ' + str(gps_lat) + ')) <= ' + str(g.distance) + ' OR stores.online = 1) limit 1,5'

        elif prod_id is not None and prod_id != '':
            generic_name = None
            print('SIMILAR GENERIC B')

            sql_query = 'SELECT optimizedSub1.*, (SELECT shopping_list.id FROM shopping_list WHERE user_id = ' + str(g.user_id) + ' AND prod_id = optimizedSub1.item_info_prod_id LIMIT 1) AS is_in_list FROM (SELECT DISTINCT item_info.*, item_info.prod_id AS item_info_prod_id FROM item_info INNER JOIN scans ON scans.prod_id = item_info.prod_id WHERE item_info.sub_category2 = (SELECT item_info.sub_category2 FROM item_info WHERE item_info.prod_id = "' + str(prod_id) + '"LIMIT 1) AND 1 = 1 AND scans.price IS NOT NULL AND scans.expiry > now() and (scans.start <= now() or scans.start is null) AND item_info.prod_id != "' + str(prod_id) + '" ORDER BY -scans.price DESC LIMIT 5) AS optimizedSub1'

        else:
            #todo handle no prod_id and no generic_name
            output['products'] = items_list_json

            result = json.dumps(output)
            return Response(result, mimetype="application/json")

        print('GENERIC QUERY')
        print(sql_query)
        #todo make this send generic similars if generic_name sent

        item_info = session.execute(sql_query)

        item_info = list(item_info)
        session.close()
        prod_id_list = []
        for row in item_info:
            if row.prod_id != '' and row.prod_id is not None:
                prod_id_list.append(row.prod_id)

        item_num = 0
        prod_id_similar = None
        for row in item_info:

            if item_num < 50:
                item_num = item_num + 1
                list_item_info = {}
                if row.prod_id is None:
                    list_item_info['prod_id'] = None
                else:
                    list_item_info['prod_id'] = str(row.prod_id)
                    prod_id_similar = row.prod_id

                if row.prod_name is None:

                    list_item_info['prod_name'] = None
                else:
                    # list_item_info['name'] = unicode(row.prod_name, errors='ignore')
                    prod_name = row.prod_name

                    brand = row.brand

                    if brand is not None and brand != '':
                        if brand not in prod_name:

                            prod_name = brand + ' ' + prod_name

                    print(prod_name)

                    prod_size = row.size
                    prod_units = row.units
                    prod_size_quantity = row.quantity
                    prod_quantity_units = row.quantity_units

                    if prod_units is not None and prod_size is not None:
                        prod_size = str(prod_size) + ' ' + str(prod_units)

                        if prod_size_quantity is not None and prod_size_quantity != '' and prod_quantity_units is None:
                            prod_size = str(prod_size_quantity) + ' x ' + str(prod_size)

                        prod_name = prod_name + ' ' + prod_size

                    list_item_info['prod_name'] = prod_name

                if row.image is None:
                    list_item_info['image'] = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/no_image_grocery_lg.png'
                    list_item_info['image_thumb'] = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/no_image_grocery_sm.png'
                else:
                    if row.awaiting_approval is None:
                        list_item_info['image'] = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME + '/sm_new/' + str(row.image)
                        list_item_info['image_thumb'] = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME + '/sm_new/' + str(row.image)
                    else:
                        list_item_info['image'] = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME + '/sm_new/' + str(row.image)
                        list_item_info['image_thumb'] = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME + '/sm_new/' + str(row.image)

                if row.is_in_list is None:
                    list_item_info['is_in_shopping_list'] = False
                else:
                    list_item_info['is_in_shopping_list'] = True

                # todo update nutrition

                list_item_info['nutr_score'] = None
                list_item_info['nutr_info'] = None

                if row.size is None:
                    size = None
                else:
                    size = str(row.size)

                if row.units is None:
                    list_item_info['size'] = size
                    units = None
                else:
                    units = str(row.units)
                    if size is not None:
                        size = str(size) + ' ' + str(row.units)
                    else:
                        size = str(row.units)

                    list_item_info['size'] = size

                all_prices = get_prices(prod_id_similar, gps_lat, gps_lng, None)
                prices = all_prices['prices']

                list_item_info['prices'] = prices

                items_list_json.append(list_item_info)

        output['products'] = items_list_json

        result = json.dumps(output)

        session.close()

        end = time.time()

        execution_time = end - start
        p_api_act = threading.Thread(target=record_api_activity, args=(
            g.user_id, gps_lat, gps_lng, '/v2/get_similar', str(get_user_ip()), execution_time),kwargs={'prod_id': prod_id, 'generic_name': generic_name})
        p_api_act.start()

        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' /v2/get_similar')
        print('Execution time (/v2/get_similar): %s' % (end - start))
        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/v2/get_similar', error_message)
        return False