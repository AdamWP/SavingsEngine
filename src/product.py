# -*- coding: utf-8 -*-
from __main__ import app
from __main__ import Session
from __main__ import g
from __main__ import Response
from __main__ import request
from __main__ import json
from __main__ import models

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
from settings import SCANS_IMAGE_BUCKET
from settings import PRODUCT_IMAGE_BUCKET_NAME
from settings import STORE_IMAGE_BUCKET


@app.route('/v2/prod_info', methods=['POST'])
@app.route('/prod_info', methods=['POST'])
@multi_auth.login_required
def api_prod_info():

    try:
        start = time.time()
        session = Session()
        
        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' /prod_info:')
        try:
            submission = request.get_json()
            print(submission)
        except Exception as e:
            print(e)
            email_crash_report('/prod_info', e)

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

        if 'prod_id' in submission:
            prod_id = submission['prod_id']
            prod_id = str(prod_id)
        else:
            result = '{"status": "missing prod_id: string"}'
            return Response(result, mimetype="application/json")

        current_store_info = get_current_store(gps_lat, gps_lng)
        current_store_id = current_store_info['current_store_id']

        item_sql = 'select item_info.brand, item_info.prod_name, item_info.size, item_info.units as size_units, item_info.quantity as quantity, item_info.quantity_units, item_info.image, (select id from urls where prod_id = "' + str(prod_id) + '" and chain = "Amazon" order by id desc limit 1) as url_id, (select quantity from shopping_list where prod_id = "' + str(prod_id) + '" and user_id = ' + str(g.user_id) + ' order by id limit 1) as is_in_list from item_info where prod_id = "' + str(prod_id) + '" limit 1'

        print(item_sql)
        item_info = session.execute(item_sql)
        session.close()

        output_record = None
        for row in item_info:
            output_record = {}

            output_record['prod_id'] = str(prod_id)

            if row.prod_name is None:
                output_record['prod_name'] = None
            else:
                prod_name = row.prod_name

                brand = row.brand

                if brand is not None and brand != '':
                    if brand.lower() not in prod_name.lower():
                        prod_name = brand + ' ' + prod_name

                prod_size = row.size
                prod_units = row.size_units
                prod_size_quantity = row.quantity
                prod_quantity_units = row.quantity_units

                if prod_units is not None and prod_size is not None:
                    prod_size = str(prod_size) + ' ' + str(prod_units)

                    if prod_size_quantity is not None and prod_size_quantity != '' and prod_quantity_units is None:
                        prod_size = str(prod_size_quantity) + ' x ' + str(prod_size)

                output_record['prod_name'] = prod_name

            output_record['size'] = prod_size

            if row.image is None:
                output_record['image'] = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/no_image_grocery_lg.png'
                output_record['image_thumb'] = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/no_image_grocery_sm.png'

            else:
                output_record['image'] = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME  + '/sm_new/' + str(row.image)
                output_record['image_thumb'] = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME + '/sm_new/' + str(row.image)

            is_in_list = row.is_in_list

            if is_in_list:
                output_record['is_in_shopping_list'] = True
                output_record['quantity'] = int(is_in_list)
            else:
                output_record['is_in_shopping_list'] = False
                output_record['quantity'] = 1

            output_record['nutr_info'] = None
            output_record['nutr_score'] = None

            all_prices = get_prices(prod_id, gps_lat, gps_lng, current_store_id)
            prices = all_prices['prices']

            output_record['prices'] = prices

            result = json.dumps(output_record)

        if output_record is None:
            result = '["Product ID does not exist"]'
            print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' ' + result)
            return Response(result, mimetype="application/json")

        end = time.time()

        execution_time = end - start

        p_api_act = threading.Thread(target=record_api_activity, args=(
            g.user_id, gps_lat, gps_lng, '/prod_info', str(get_user_ip()), execution_time), kwargs={'prod_id': prod_id})
        p_api_act.start()

        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' /prod_info')
        print('Execution time (/prod_info): %s' % (end - start))
        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/prod_info', error_message)
        return False
