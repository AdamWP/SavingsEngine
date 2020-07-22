# -*- coding: utf-8 -*-
from __main__ import app
from __main__ import Session
from __main__ import Session_main
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

from decimal import Decimal, getcontext

from src.authentication import multi_auth
from src.email import email_crash_report
from src.utils import get_user_ip
from src.utils import check_gps
from src.utils import record_api_activity

from src.stores import get_current_store
from src.prices import get_prices
from src.prices import get_best_price
from src.points import redeem_points_token
from src.points import add_points

from settings import S3_ENDPOINT
from settings import SCANS_IMAGE_BUCKET
from settings import PRODUCT_IMAGE_BUCKET_NAME
from settings import STORE_IMAGE_BUCKET


@app.route('/shopping_list', methods=['POST'])
@app.route('/v2/shopping_list', methods=['POST'])
@multi_auth.login_required
def api_shopping_list_v2():
    try:
        start = time.time()
        session = Session()

        shopping_list_json = []

        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' /v2/shopping_list:')

        try:
            submission = request.get_json()

        except Exception as e:
            print(e)
            email_crash_report('/v2/shopping_list', e)
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

        current_store_info = get_current_store(gps_lat, gps_lng)
        current_store_id = current_store_info['current_store_id']

        sql_list = 'select * from (select * from shopping_list where shopping_list.user_id = ' + str(g.user_id) + ' and (prod_id is not null or generic_name is not null))t1 left join item_info on item_info.prod_id = t1.prod_id left join shopping_list_generic on shopping_list_generic.name = t1.generic_name'

        print(sql_list)

        item_info = session.execute(sql_list)
        item_info = list(item_info)
        session.close()

        prod_id_list = []

        for row in item_info:
            if row.prod_id != '' and row.prod_id is not None:

                prod_id_list.append(row.prod_id)

        for row in item_info:

            shopping_list_record = {}

            if row.generic_name is None:
                shopping_list_record['generic_name'] = None

            else:
                shopping_list_record['generic_name'] = str(row.generic_name)

            if row.generic_name is None:
                shopping_list_record['bg_colour'] = '#FFFFFF00'

            else:
                shopping_list_record['bg_colour'] = '#B1B1B110'

            if row.icon is None:
                shopping_list_record['icon'] = 'https://www.topsavings.com/static/shopping_list_icons/smart_product.png'
                shopping_list_record['icon'] = 'https://www.topsavings.com/static/smart_icons_light/smart_product.png'

            else:
                shopping_list_record['icon'] = 'https://www.topsavings.com/static/shopping_list_icons/' + str(row.icon)
                shopping_list_record['icon_light'] = 'https://www.topsavings.com/static/smart_icons_light/' + str(row.icon)

            if row.prod_id is None:
                shopping_list_record['prod_id'] = None
                prod_id = None
            else:
                shopping_list_record['prod_id'] = str(row.prod_id)
                prod_id = str(row.prod_id)

            if prod_id is None:
                shopping_list_record['image'] = None
                shopping_list_record['image_thumb'] = None

            elif row.image is None:
                shopping_list_record['image'] = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/no_image_grocery_lg.png'
                shopping_list_record[
                    'image_thumb'] = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/no_image_grocery_sm.png'
            elif row.awaiting_approval is not None:
                shopping_list_record['image'] = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME + '/sm_new/' + str(
                    row.image)
                shopping_list_record['image_thumb'] = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME + '/sm_new/' + str(
                    row.image)
            else:
                shopping_list_record['image'] = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME + '/sm_new/' + str(
                    row.image)
                shopping_list_record['image_thumb'] = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME + '/sm_new/' + str(
                    row.image)

            # todo update nutrition
            shopping_list_record['nutr_score'] = None
            shopping_list_record['nutr_info'] = None

            if row.prod_name is None:
                shopping_list_record['prod_name'] = None
                prod_size = None
            else:
                prod_name = row.prod_name
                brand = row.brand

                if brand is not None and brand !='':
                    if brand not in prod_name:
                        prod_name = brand + ' ' + prod_name

                prod_size = row.size
                prod_units = row.units
                prod_size_quantity = row.quantity
                prod_quantity_units = row.quantity_units

                if prod_units is not None and prod_size is not None:
                    prod_size = str(prod_size) + ' ' + str(prod_units)

                    if prod_size_quantity is not None and prod_size_quantity != '' and prod_quantity_units is None:
                        prod_size = str(prod_size_quantity) + ' x ' + str(prod_size)

                shopping_list_record['prod_name'] = prod_name

            shopping_list_record['size'] = prod_size

            if row.quantity is None:
                shopping_list_record['quantity'] = 1
            else:
                shopping_list_record['quantity'] = row.quantity

            if row.checked is None:
                shopping_list_record['is_checked'] = False
            else:
                shopping_list_record['is_checked'] = True

            if row.list_add_time is None:
                shopping_list_record['date_added'] = None
            else:
                add_time = row.list_add_time
                add_time = str(add_time)
                shopping_list_record['date_added'] = (time.mktime(time.strptime(add_time, '%Y-%m-%d %H:%M:%S'))) - time.timezone

            if prod_id is not None and prod_id != '':
                all_prices = get_prices(prod_id, gps_lat, gps_lng, current_store_id)
                prices = all_prices['prices']

            else:
                prices = None

            shopping_list_record['prices'] = prices

            if prices is None:

                shopping_list_record['store_id'] = None
                shopping_list_record['url'] = None
                shopping_list_record['store'] = None
                shopping_list_record['store_image'] = None
                shopping_list_record['store_logo'] = None
                shopping_list_record['store_thumb'] = None
                shopping_list_record['store_name'] = None
                shopping_list_record['store_address'] = None
                shopping_list_record['currency'] = None
                shopping_list_record['price'] = None
                shopping_list_record['saving_price'] = None
                shopping_list_record['date_time'] = None

            elif len(prices) > 0:
                best_store_name = prices[0]['store_name']
                if best_store_name != 'Amazon':
                    shopping_list_record['store_id'] = prices[0]['store_id']
                    shopping_list_record['url'] = prices[0]['url']

                    shopping_list_record['store_image'] = prices[0]['store_image']
                    shopping_list_record['store_logo'] = prices[0]['store_image']
                    shopping_list_record['store_thumb'] = prices[0]['store_thumb']
                    shopping_list_record['store_name'] = prices[0]['store_name']
                    shopping_list_record['store_address'] = prices[0]['store_address']

                    price = prices[0]['price']
                    if price is not None:

                        shopping_list_record['currency'] = '$'
                        shopping_list_record['price'] = price
                    else:
                        shopping_list_record['currency'] = None
                        shopping_list_record['price'] = None

                    saving_price = prices[0]['saving_price']
                    if saving_price is not None:

                        shopping_list_record['saving_price'] = saving_price
                    else:
                        shopping_list_record['saving_price'] = None
                    #shopping_list_record['date_time'] = prices[0]['date_time']
                elif len(prices) > 1:
                    shopping_list_record['store_id'] = prices[1]['store_id']
                    shopping_list_record['url'] = prices[1]['url']
                    shopping_list_record['store_image'] = prices[1]['store_image']
                    shopping_list_record['store_logo'] = prices[1]['store_image']
                    shopping_list_record['store_thumb'] = prices[1]['store_thumb']
                    shopping_list_record['store_name'] = prices[1]['store_name']
                    shopping_list_record['store_address'] = prices[1]['store_address']
                    price = prices[0]['price']
                    if price is not None:
                        shopping_list_record['currency'] = '$'
                        shopping_list_record['price'] = price
                    else:
                        shopping_list_record['currency'] = None
                        shopping_list_record['price'] = None

                    saving_price = prices[0]['saving_price']

                    shopping_list_record['saving_price'] = saving_price

                    shopping_list_record['date_time'] = prices[1]['date_time']
                else:
                    shopping_list_record['store_id'] = None
                    shopping_list_record['url'] = None
                    shopping_list_record['store'] = None
                    shopping_list_record['store_image'] = None
                    shopping_list_record['store_logo'] = None
                    shopping_list_record['store_thumb'] = None
                    shopping_list_record['store_name'] = None
                    shopping_list_record['store_address'] = None
                    shopping_list_record['currency'] = None
                    shopping_list_record['price'] = None
                    shopping_list_record['saving_price'] = None
                    shopping_list_record['date_time'] = None

            else:
                shopping_list_record['store_id'] = None
                shopping_list_record['url'] = None
                shopping_list_record['store'] = None
                shopping_list_record['store_image'] = None
                shopping_list_record['store_logo'] = None
                shopping_list_record['store_thumb'] = None
                shopping_list_record['store_name'] = None
                shopping_list_record['store_address'] = None
                shopping_list_record['currency'] = None
                shopping_list_record['price'] = None
                shopping_list_record['saving_price'] = None
                shopping_list_record['date_time'] = None

            shopping_list_json.append(shopping_list_record)

        output_record = {}

        output_record['list'] = shopping_list_json

        result = json.dumps(output_record)
        session.close()
        end = time.time()
        execution_time = end - start
        p_api_act = threading.Thread(target=record_api_activity, args=(g.user_id, gps_lat, gps_lng, '/v2/shopping_list', str(get_user_ip()), execution_time))
        p_api_act.start()

        print('Execution time (/v2/shopping_list): %s' % (end - start))

        return Response(result, mimetype="application/json")

    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/v2/shopping_list', error_message)
        return False


@app.route('/v2/shopping_list_suggestions', methods=['POST'])
@multi_auth.login_required
def api_shopping_list_suggestions():
    try:

        start = time.time()
        session = Session()

        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(
            g.user_id) + ' /v2/shopping_list_suggestions:')

        try:
            submission = request.get_json()

        except Exception as e:
            print(e)
            email_crash_report('/v2/shopping_list_suggestions', e)
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

        sql_list = 'select * from shopping_list_generic where rank is not null and not exists (select id from shopping_list where generic_name = shopping_list_generic.name and user_id = ' + str(g.user_id) + ') order by rank limit 5'

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
                # list_record['bg_colour'] = '#F2FF0010'
                list_record['bg_colour'] = '#B1B1B110'

                generic_list.append(list_record)

        suggested_list = {}
        suggested_list['title'] = 'Add Smart Products'
        suggested_list['text'] = 'By comparing brands and sizes, the product with the lowest unit price is found at a store near you.'

        suggested_list['image'] = 'https://www.topsavings.com/appimages/smart_products.png'

        suggested_list['info_id'] = 'smart products'

        suggested_list['list_suggestions'] = generic_list

        result = json.dumps(suggested_list)

        session.close()

        end = time.time()

        execution_time = end - start
        p_api_act = threading.Thread(target=record_api_activity, args=(
            g.user_id, gps_lat, gps_lng, '/v2/shopping_list_suggestions', str(get_user_ip()), execution_time))
        p_api_act.start()

        print('Execution time (/v2/shopping_list_suggestions): %s' % (end - start))

        return Response(result, mimetype="application/json")

    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/v2/shopping_list_suggestions', error_message)
        return False


@app.route('/v2/set_checked', methods=['POST'])
@app.route('/set_checked', methods=['POST'])
@multi_auth.login_required
def api_set_checked():
    try:
        start = time.time()
        session = Session()
        output = []

        print( str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' /v2/set_checked:')

        try:
            submission = request.get_json()

        except Exception as e:
            print(e)
            email_crash_report('/set_checked', e)

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
                return Response(result, mimetype="application/json")
        else:
            result = '{"status": "GPS Error"}'
            return Response(result, mimetype="application/json")

        if 'prod_id' in submission:
            prod_id = submission['prod_id']
        else:
            result = '{"status": "missing prod_id: string"}'
            return Response(result, mimetype="application/json")

        if 'is_checked' in submission:
            is_checked = submission['is_checked']
        else:
            result = '{"status": "missing is_checked: boolean"}'
            return Response(result, mimetype="application/json")

        result = {}

        if is_checked is True:

            p_check = threading.Thread(target=update_checked, args=(g.user_id, prod_id, True))
            p_check.start()

            p_add_user_savings = threading.Thread(target=add_user_savings, args=(g.user_id, g.distance, 'check_list_item', gps_lat, gps_lng, prod_id, None))
            p_add_user_savings.start()

            result['is_checked'] = True
        else:
            p_check = threading.Thread(target=update_checked, args=(g.user_id, prod_id, False))
            p_check.start()

            result['is_checked'] = False

        result = json.dumps(result)

        session.close()

        end = time.time()
        execution_time = end - start

        p_api_act = threading.Thread(target=record_api_activity, args=(g.user_id, gps_lat, gps_lng, '/set_checked', str(get_user_ip()), execution_time), kwargs={'prod_id': prod_id})
        p_api_act.start()

        print('Execution time (/set_checked): %s' % (end - start))
        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/set_checked', error_message)
        return False


def update_checked(user_id, prod_id, check_status):
    session = Session()
    session_main = Session_main()

    if check_status is True:

        sql_query = 'update shopping_list set checked = 1 where user_id = ' + str(user_id) + ' and (prod_id = "' + str(prod_id) + '" or generic_name = "' + str(prod_id) + '")'

        session.execute(sql_query)
        session.commit()
        session.close()

        session_main.execute(sql_query)
        session_main.commit()
        session_main.close()

        shopping_list_items_unchecked = session.query(
            models.shopping_list).filter(
            (models.shopping_list.user_id == user_id) &
            (models.shopping_list.checked is None)
        ).first()
        session.close()
        if not shopping_list_items_unchecked:

            since = datetime.datetime.now() - datetime.timedelta(hours=24)
            shopping_list_completed = session.query(models.shopping_lists_completed).filter(
                (models.shopping_lists_completed.user_id == user_id) &
                (models.shopping_lists_completed.date_time > since)
            ).first()
            session.close()

            if not shopping_list_completed:
                sql_query = 'insert into shopping_lists_completed (date_time, user_id, list_size) values (now(),"' + str(
                    user_id) + '",(select count(*) from shopping_list where user_id = "' + str(user_id) + '"))'

                session.execute(sql_query)
                session.commit()
                session.close()

    else:
        sql_query = 'update shopping_list set checked = null where user_id = ' + str(
            user_id) + ' and (prod_id = "' + str(prod_id) + '" or generic_name = "' + str(prod_id) + '")'
        session.execute(sql_query)
        session.commit()
        session.close()

        session_main.execute(sql_query)
        session_main.commit()
        session_main.close()

    return False


@app.route('/v2/clear_shopping_list', methods=['GET', 'POST'])
@app.route('/clear_shopping_list', methods=['GET', 'POST'])
@multi_auth.login_required
def api_clear_shopping_list():
    try:
        start = time.time()
        session = Session()

        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(
            g.user_id) + ' /v2/clear_shopping_list:')

        try:
            submission = request.get_json()

        except Exception as e:
            print(e)
            email_crash_report('/v2/clear_shopping_list', e)

            result = '{"status": "MUST BE IN JSON FORMAT"}'
            return Response(result, mimetype="application/json")

        if 'gps' in submission:
            gps = submission['gps']
            gps_info = check_gps(gps)
            if gps_info:
                gps_lat = gps_info['gps_lat']
                gps_lng = gps_info['gps_lng']
            else:
                result = '{"status": "missing gps"}'
                return Response(result, mimetype="application/json")
        else:
            result = '{"status": "GPS Error"}'
            return Response(result, mimetype="application/json")

        p_update_list = threading.Thread(target=update_list, args=(g.user_id,))
        p_update_list.start()

        sql_query = 'delete from shopping_list where user_id = ' + str(g.user_id)

        session.execute(sql_query)
        session.commit()
        session.close()

        result = '{"status": "shopping list cleared"}'

        end = time.time()

        execution_time = end - start

        p_api_act = threading.Thread(target=record_api_activity, args=(
        g.user_id, gps_lat, gps_lng, 'clear_shopping_list', str(get_user_ip()), execution_time))
        p_api_act.start()

        print('Execution time (/v2/clear_shopping_list): %s' % (end - start))
        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/v2/clear_shopping_list', error_message)
        return False


def update_list(user_id):
    session_main = Session_main()

    sql_query = 'update shopping_list set expired = now() where user_id = ' + str(user_id) + ' and expired is null'

    session_main.execute(sql_query)
    session_main.commit()
    session_main.close()

    return False


@app.route('/v2/reset_shopping_list', methods=['POST'])
@app.route('/reset_shopping_list', methods=['POST'])
@multi_auth.login_required
def api_reset_shopping_list():
    try:
        start = time.time()
        session = Session()
        session_main = Session_main()

        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(
            g.user_id) + ' /reset_shopping_list:')
        try:
            submission = request.get_json()

        except Exception as e:
            print(e)
            email_crash_report('/reset_shopping_list', e)

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
                return Response(result, mimetype="application/json")
        else:
            result = '{"status": "GPS Error"}'
            return Response(result, mimetype="application/json")

        str_sql = 'update shopping_list set checked = null where user_id = "' + str(g.user_id) + '" and expired is null'
        session_main.execute(str_sql)
        session_main.commit()
        session_main.close()

        str_sql = 'update shopping_list set checked = null where user_id = "' + str(
            g.user_id) + '"'
        session.execute(str_sql)
        session.commit()
        session.close()

        result = '{"shopping list reset"}'

        end = time.time()

        execution_time = end - start

        p_api_act = threading.Thread(target=record_api_activity, args=(
            g.user_id, gps_lat, gps_lng, 'reset_shopping_list', str(get_user_ip()), execution_time))
        p_api_act.start()

        print('Execution time (reset_shopping_list): %s' % (end - start))
        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/reset_shopping_list', error_message)
        return False


@app.route('/set_shopping_list', methods=['POST'])
@multi_auth.login_required
def api_set_shopping_list():
    try:
        start = time.time()
        session = Session()
        points = None
        points_message = None

        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' /set_shopping_list:')
        try:
            submission = request.get_json()

        except Exception as e:
            print(e)
            email_crash_report('/set_shopping_list', e)

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

                return Response(result, mimetype="application/json")
        else:
            result = '{"status": "GPS Error"}'
            return Response(result, mimetype="application/json")
        if 'prod_id' in submission:
            prod_id = submission['prod_id']
        else:
            result = '{"status": "missing prod_id : string/null"}'

            return Response(result, mimetype="application/json")
        if 'is_in_shopping_list' in submission:
            is_in_shopping_list = submission['is_in_shopping_list']
        else:
            result = '{"status": "missing is_in_shopping_list : boolean"}'

            return Response(result, mimetype="application/json")

        if 'points_token' in submission:
            points_token = submission['points_token']
        else:
            result = '{"status": "missing points_token : string/null"}'

            return Response(result, mimetype="application/json")
        if 'added_from' in submission:
            added_from = submission['added_from']
        else:
            result = '{"status": "missing added_from : JSON Object"}'

            return Response(result, mimetype="application/json")

        if 'deal_id' in added_from:
            deal_id = added_from['deal_id']
            if deal_id is not None:
                deal_id = deal_id.strip()
            if deal_id == '':
                deal_id = None
        else:

            result = '{"status": "missing deal_id : string/null"}'

            return Response(result, mimetype="application/json")

        if 'search_query' in added_from:
            search_query = added_from['search_query']
            if search_query is not None:
                search_query = search_query.strip()
            if search_query == '':
                search_query = None


        else:
            result = '{"status": "missing search_query : string/null"}'

            return Response(result, mimetype="application/json")
        if 'scan_id' in added_from:
            scan_id = added_from['scan_id']
            if scan_id is not None:
                scan_id = scan_id.strip()
            if scan_id == '':
                scan_id = None
        else:
            result = '{"status": "missing scan_id : string/null"}'
            return Response(result, mimetype="application/json")

        if 'prod_info' in added_from:
            prod_info = added_from['prod_info']
            if not isinstance(prod_info, bool):
                prod_info = False
        else:
            result = '{"status": "missing prod_info : boolean"}'

            return Response(result, mimetype="application/json")

        result = {}
        if is_in_shopping_list is True:
            if 'points_token' in submission:
                points_token = submission['points_token']
                points_info = redeem_points_token(points_token, prod_id)
                points = points_info['points']
                points_message = points_info['points_message']

            # todo use shopping_list
            list_info = session.query(models.shopping_list).filter(
                (models.shopping_list.prod_id == prod_id) &
                (models.shopping_list.user_id == g.user_id) &
                (models.shopping_list.expired is None)
            ).distinct().first()
            session.close()
            if not list_info:

                if points is None:

                    # check if points have been given for adding to list in past 24 hours.  if not then award points.  Waiting for UI
                    since = datetime.datetime.now() - datetime.timedelta(hours=24)
                    check_recent = session_main.query(models.points).filter(
                        (models.points.prod_id == prod_id) &
                        (models.points.user_id == g.user_id) &
                        (models.points.reward_type == 'add_to_list') &
                        (models.points.earned_on > since)
                    ).distinct().count()
                    session_main.close()

                    if check_recent < 1:
                        points = 1
                        points_message = 'Item Added to Shopping List!'
                        add_points(g.user_id, points, 'add_to_list', None, prod_id, None, None)

                update_shopping_list(g.user_id, prod_id, None, True, gps_lat, gps_lng, deal_id, search_query, scan_id, prod_info)
                p_add_savings = threading.Thread(target=add_user_savings, args=(g.user_id, g.distance, 'add_to_list', gps_lat, gps_lng, prod_id, None))
                p_add_savings.start()

            result['is_in_shopping_list'] = True
        else:

            update_shopping_list(g.user_id, prod_id, None, False, gps_lat, gps_lng, deal_id, search_query, scan_id, prod_info)

            result['is_in_shopping_list'] = False

        result['points'] = points
        result['points_message'] = points_message

        result = json.dumps(result)
        session.commit()
        session.close()

        session.close()
        end = time.time()

        execution_time = end - start
        p_api_act = threading.Thread(target=record_api_activity, args=(
            g.user_id, gps_lat, gps_lng, 'set_shopping_list', str(get_user_ip()), execution_time))
        p_api_act.start()

        print('Execution time (set_shopping_list): %s' % (end - start))
        return Response(result, mimetype="application/json")

    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/set_shopping_list', error_message)
        return False


@app.route('/v2/set_shopping_list', methods=['POST'])
@multi_auth.login_required
def api_set_shopping_list_v2():
    try:
        start = time.time()
        session = Session()
        session_main = Session_main()
        points = None
        points_message = None

        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(
            g.user_id) + ' /v2/set_shopping_list:')
        try:
            submission = request.get_json()
        except Exception as e:
            print(e)
            email_crash_report('/v2/set_shopping_list', e)

            result = '{"status": "MUST BE IN JSON FORMAT"}'
            print(result)
            return Response(result, mimetype="application/json")

        if 'gps' in submission:
            gps = submission['gps']
            gps_info = check_gps(gps)
            if gps_info:
                gps_lat = gps_info['gps_lat']
                gps_lng = gps_info['gps_lng']
            else:
                result = '{"status": "GPS Error"}'
                print(result)
                return Response(result, mimetype="application/json")
        else:
            result = '{"status": "GPS Error"}'
            print(result)
            return Response(result, mimetype="application/json")
        if 'prod_id' in submission:
            prod_id = submission['prod_id']
        else:
            result = '{"status": "missing prod_id : string/null"}'

        if 'generic_name' in submission:
            generic_name = submission['generic_name']
        else:
            result = '{"status": "missing generic_name : string/null"}'
            print(result)
            return Response(result, mimetype="application/json")
        if 'is_in_shopping_list' in submission:
            is_in_shopping_list = submission['is_in_shopping_list']
        else:
            result = '{"status": "missing is_in_shopping_list : boolean"}'
            print(result)
            return Response(result, mimetype="application/json")

        if 'points_token' in submission:
            points_token = submission['points_token']
        else:
            result = '{"status": "missing points_token : string/null"}'
            print(result)
            return Response(result, mimetype="application/json")

        if 'added_from' in submission:
            added_from = submission['added_from']
        else:
            result = '{"status": "missing added_from : JSON Object"}'
            print(result)
            return Response(result, mimetype="application/json")

        if 'deal_id' in added_from:
            deal_id = added_from['deal_id']
            if deal_id is not None:
                deal_id = deal_id.strip()
            if deal_id == '':
                deal_id = None
        else:

            result = '{"status": "missing deal_id : string/null"}'
            print(result)
            return Response(result, mimetype="application/json")

        if 'search_query' in added_from:
            search_query = added_from['search_query']
        else:
            result = '{"status": "missing search_query : string/null"}'
            print(result)
            return Response(result, mimetype="application/json")

        if 'category' in added_from:
            category = added_from['category']

        else:
            category = None

        if 'scan_id' in added_from:
            scan_id = added_from['scan_id']
            if scan_id is not None:
                scan_id = scan_id.strip()
            if scan_id == '':
                scan_id = None
        else:
            result = '{"status": "missing scan_id : string/null"}'
            print(result)
            return Response(result, mimetype="application/json")

        if 'prod_info' in added_from:
            prod_info = added_from['prod_info']
            if not isinstance(prod_info, bool):
                prod_info = False
        else:
            result = '{"status": "missing prod_info : boolean"}'
            print(result)
            return Response(result, mimetype="application/json")

        result = {}
        if is_in_shopping_list is True:
            if 'points_token' in submission:
                points_token = submission['points_token']
                points_info = redeem_points_token(points_token, prod_id)
                points = points_info['points']
                points_message = points_info['points_message']

            list_info = session.query(models.shopping_list).filter(
                (models.shopping_list.prod_id == prod_id) &
                (models.shopping_list.generic_name == generic_name) &
                (models.shopping_list.user_id == g.user_id)
            ).distinct().first()
            session.close()
            if not list_info:

                if points is None:

                    # check if points have been given for adding to list in past 24 hours.  if not then award points.  Waiting for UI
                    since = datetime.datetime.now() - datetime.timedelta(hours=24)
                    check_recent = session_main.query(models.points).filter(
                        (models.points.prod_id == prod_id) &
                        (models.points.user_id == g.user_id) &
                        (models.points.reward_type == 'add_to_list') &
                        (models.points.earned_on > since)
                    ).distinct().count()
                    session_main.close()

                    if check_recent < 1:
                        points = 1
                        points_message = 'Item Added to Shopping List!'
                        add_points(g.user_id, points, 'add_to_list', None, prod_id, None, None)

                update_shopping_list(g.user_id, prod_id, generic_name, True, gps_lat, gps_lng, deal_id, search_query, scan_id, prod_info)

                if prod_id is not None and prod_id != '':
                    p_add_savings = threading.Thread(target=add_user_savings, args=(g.user_id, g.distance, 'add_to_list', gps_lat, gps_lng, prod_id, None))
                    p_add_savings.start()

            result['is_in_shopping_list'] = True
        else:

            update_shopping_list(g.user_id, prod_id, generic_name, False, gps_lat, gps_lng, deal_id, search_query,
                                 scan_id, prod_info)

            result['is_in_shopping_list'] = False

        result['points'] = points
        result['points_message'] = points_message

        result = json.dumps(result)
        session.commit()
        session.close()

        session.close()
        end = time.time()

        execution_time = end - start
        p_api_act = threading.Thread(target=record_api_activity, args=(
            g.user_id, gps_lat, gps_lng, '/v2/set_shopping_list', str(get_user_ip()), execution_time), kwargs={'user_activity': 1, 'prod_id': prod_id, 'generic_name': generic_name})
        p_api_act.start()

        print('Execution time (/v2/set_shopping_list): %s' % (end - start))
        return Response(result, mimetype="application/json")
        # return result
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/v2/set_shopping_list', error_message)
        result = '{"status": "/v2/set_shopping_list error"}'

        return Response(result, mimetype="application/json")


def update_shopping_list(user_id, prod_id, generic_name, list_status, gps_lat, gps_lng, deal_id, search_query, scan_id, prod_info):
    session = Session()
    session_main = Session_main()

    if prod_info is True:
        prod_info = '1'
    else:
        prod_info = None

    if list_status is True:
        sql_query_a = 'insert into shopping_list(user_id, quantity, list_add_time, gps_lat, gps_lng'
        sql_query_b = ') values(' + str(user_id) + ', 1, now(), "' + str(gps_lat) + '","' + str(gps_lng) + '"'

        if prod_id is not None:
            sql_query_a = sql_query_a + ', prod_id'
            sql_query_b = sql_query_b + ',"' + str(prod_id) + '"'

        if generic_name is not None:
            sql_query_a = sql_query_a + ', generic_name'
            sql_query_b = sql_query_b + ',"' + str(generic_name) + '"'

        if deal_id is not None:
            sql_query_a = sql_query_a + ', deal_id'
            sql_query_b = sql_query_b + ',"' + str(deal_id) + '"'

        if search_query is not None:
            sql_query_a = sql_query_a + ', search_query'
            sql_query_b = sql_query_b + ',"' + str(search_query) + '"'

        if scan_id is not None:
            sql_query_a = sql_query_a + ', scan_id'
            sql_query_b = sql_query_b + ',"' + str(scan_id) + '"'

        if prod_info is not None:
            sql_query_a = sql_query_a + ', prod_info'
            sql_query_b = sql_query_b + ',"' + str(prod_info) + '"'

        sql_query = sql_query_a + sql_query_b + ')'

        session_main.execute(sql_query)
        session_main.commit()
        session_main.close()

        sql_query_a = 'insert into shopping_list(user_id'
        sql_query_b = ') values(' + str(user_id)

        if prod_id is not None:
            sql_query_a = sql_query_a + ', prod_id'
            sql_query_b = sql_query_b + ',"' + str(prod_id) + '"'

        if generic_name is not None:
            sql_query_a = sql_query_a + ', generic_name'
            sql_query_b = sql_query_b + ',"' + str(generic_name) + '"'

        sql_query = sql_query_a + sql_query_b + ')'

        session.execute(sql_query)
        session.commit()
        session.close()

    else:

        if prod_id is not None and prod_id != '':
            sql_query = 'delete from shopping_list where user_id = ' + str(user_id) + ' and prod_id = "' + str(prod_id) + '"'
        elif generic_name is not None and generic_name != '':
            sql_query = 'delete from shopping_list where user_id = ' + str(user_id) + ' and generic_name = "' + str(generic_name) + '"'

        session.execute(sql_query)
        session.commit()
        session.close()

        if prod_id is not None and prod_id != '':
            sql_query = 'update shopping_list set expired = now() where user_id = ' + str(user_id) + ' and prod_id = "' + str(prod_id) + '" and expired is null'
        elif generic_name is not None and generic_name != '':
            sql_query = 'update shopping_list set expired = now() where user_id = ' + str(user_id) + ' and generic_name = "' + str(generic_name) + '" and expired is null'

        session_main.execute(sql_query)
        session_main.commit()
        session_main.close()

    return False


def add_user_savings(user_id, distance, savings_type, gps_lat, gps_lng, prod_id, scan_id):
    try:
        session = Session()
        session_main = Session_main()

        current_store_info = get_current_store(gps_lat, gps_lng)
        current_store_id = current_store_info['current_store_id']

        best_price_info = get_best_price(user_id, distance, gps_lat, gps_lng, prod_id, current_store_id, None, None)

        if best_price_info['saving_price'] != '' and best_price_info['saving_price'] is not None:

            # check if savings price has been added to db in past 24 hours
            since = datetime.datetime.now() - datetime.timedelta(hours=24)
            check_recent = session.query(models.user_savings).filter(
                (models.user_savings.prod_id == prod_id) &
                (models.user_savings.user_id == user_id) &
                (models.user_savings.post_time > since)
            ).distinct().count()
            session.close()

            if check_recent < 1:
                saving_price = str(best_price_info['saving_price'])
                submission = models.user_savings(
                    user_id=int(user_id),
                    savings=saving_price,
                    savings_type=savings_type,
                    prod_id=prod_id,
                    scan_id=scan_id,
                    post_time=datetime.datetime.utcnow()
                )

                session.add(submission)
                session.commit()
                session.close()

                session_main.add(submission)
                session_main.commit()
                session_main.close()

        return False
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('add_user_savings', error_message)
        return False
