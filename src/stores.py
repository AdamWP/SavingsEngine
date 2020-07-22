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


from settings import S3_ENDPOINT
from settings import STORE_IMAGE_BUCKET


@app.route('/stores', methods=['POST'])
@app.route('/v2/stores', methods=['POST'])
@multi_auth.login_required
def api_stores_v2():
    try:

        start = time.time()
        session = Session()
        output = []
        stores_list_json = []
        savings_from = ''
        savings_from_temp = ''
        savings_from_count = 0
        savings_from_count_disp = 0

        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' /v2/stores:')
        try:
            submission = request.get_json()
        except Exception as e:
            print(e)
            email_crash_report('/v2/stores', e)

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

        savings_total = None
        price_total = None

        item_info = session.query(models.user).filter(
            (models.user.id == g.user_id)).distinct().first()
        session.close()

        output_record = {}
        if item_info:
            unit_type = g.user_units
            if unit_type == 'i':
                units = 'mi'
            else:
                units = 'KM'

            if item_info.distance is None:
                output_record['range'] = 5
                output_record['range_units'] = str(units)
            else:
                output_record['range'] = int(item_info.distance)
                output_record['range_units'] = str(units)
            output_record['range_min'] = 1
            output_record['range_max'] = 50
            output_record['savings_total'] = savings_total
            output_record['savings_currency'] = '$'
            output_record['total'] = price_total
            output_record['total_currency'] = '$'


            sql_query = 'select *, (select prod_id from deals.zone_deals where prod_id is not null and chain = t1.chain and expiry > now() and zone_id = "' + str(g.zone_id) + '" limit 1) as deal_id from (select stores.address, stores.id, stores.logo, stores.store_theme_color, stores.store_bg_is_light, stores.chain, (select st_distance_sphere(stores.pt, Point(' + gps_lng + ', ' + gps_lat + '))) AS store_dist, (select user_id from user_stores_disabled where chain = stores.chain and user_id = ' + str(g.user_id) + ' limit 1)as disabled from stores where (' + str(g.distance) + ' >= (select st_distance_sphere(stores.pt, Point(' + gps_lng + ', ' + gps_lat + ')))  or stores.online = 1) order by chain, store_dist) as t1 group by chain'

            user_stores_result = session.execute(sql_query)
            session.close()
            for row in user_stores_result:
                stores_list = {}

                if row.chain != '' and row.chain is not None:
                    name = row.chain
                    chain = row.chain
                    if len(savings_from_temp) > 0:
                        savings_from_temp = savings_from + ', ' + chain
                    else:
                        savings_from_temp = chain

                    if 20 >= len(savings_from_temp) > 0:
                        savings_from = savings_from_temp
                        savings_from_count_disp = savings_from_count_disp + 1

                    savings_from_count = savings_from_count + 1

                else:
                    name = None
                    chain = None

                stores_list['name'] = name

                if row.chain != '' and row.chain is not None:
                    id = row.chain
                    store_id = id
                    id = id.lower()
                    id = id.strip()
                else:
                    id = None
                    store_id = None

                stores_list['id'] = str(id)

                if row.disabled is not None and row.disabled != '':
                    is_enabled = False
                    stores_list['is_enabled'] = False
                else:
                    is_enabled = True
                    stores_list['is_enabled'] = True

                if row.deal_id is not None and row.deal_id != '':
                    stores_list['has_deals'] = True
                else:
                    stores_list['has_deals'] = False

                if row.logo != '' and row.logo is not None:
                    logo = row.logo
                    store_logo = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/stores/' + logo
                    store_thumb = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/stores_sm/' + logo
                    store_bg = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/store_backgrounds/' + logo

                    stores_list['store_logo'] = store_logo
                    stores_list['store_thumb'] = store_thumb
                    if g.user_id == 3 or g.user_id == 210 or g.user_id == 1 or g.user_id == 189:
                        stores_list['store_bg'] = store_bg
                    else:
                        stores_list['store_bg'] = None
                else:
                    logo = None
                    stores_list['store_logo'] = None
                    stores_list['store_thumb'] = None
                    stores_list['store_bg'] = None

                if row.store_theme_color is not None and row.store_theme_color != '' and (g.user_id == 3 or g.user_id == 210 or g.user_id == 1 or g.user_id == 189):

                    stores_list['store_theme_color'] = '#' + str(row.store_theme_color)
                else:
                    stores_list['store_theme_color'] = '#000000'

                if row.store_bg_is_light is not None and (g.user_id == 3 or g.user_id == 210 or g.user_id == 1):
                    stores_list['store_bg_is_light'] = True
                else:
                    stores_list['store_bg_is_light'] = False

                locations = []
                location = {}

                str_sql_locations = 'select stores.id, stores.name, stores.address, stores.gps_lat, stores.gps_lng, stores.online, (select st_distance_sphere(stores.pt, Point(' + gps_lng + ', ' + gps_lat + '))) AS store_dist from stores where stores.chain = "' + chain + '" and (' + str(g.distance) + ' >= (select st_distance_sphere(stores.pt, Point(' + gps_lng + ', ' + gps_lat + '))) or stores.online = 1) order by store_dist'

                store_locations = session.execute(str_sql_locations)
                session.close()
                for row_locations in store_locations:
                    location = {}
                    if row_locations.id is not None and row_locations.id != '':
                        location['store_id'] = str(row_locations.id)

                    else:
                        location['store_id'] = None

                    if row_locations.address is not None and row_locations.address != '':

                        address = str(row_locations.name)

                        location['address'] = address

                    else:
                        location['address'] = None

                    if row_locations.gps_lat is not None and row_locations.gps_lat != '' and row_locations.online != 1:
                        location['gps_lat'] = str(row_locations.gps_lat)

                    else:
                        location['gps_lat'] = None

                    if row_locations.gps_lng is not None and row_locations.gps_lng != '' and row_locations.online != 1:
                        location['gps_lng'] = str(row_locations.gps_lng)

                    else:
                        location['gps_lng'] = None

                    if row_locations.online == 1:
                        store_dist = 1000
                    elif row_locations.store_dist != '' and row_locations.store_dist is not None:
                        store_dist = row_locations.store_dist
                        store_dist = store_dist / 1000
                        store_dist = round(store_dist, 2)
                        # store_dist = str(store_dist) + ' ' + units
                    else:
                        store_dist = None

                    location['distance'] = store_dist

                    locations.append(location)

                stores_list['locations'] = locations

                stores_list_json.append(stores_list)

            output_record['stores'] = stores_list_json

            stores_count = savings_from_count
            savings_from_count = savings_from_count - savings_from_count_disp
            savings_from = savings_from + ' +' + str(savings_from_count)
            output_record['savings_from'] = savings_from
            output_record['stores_count'] = stores_count

        result = json.dumps(output_record)

        session.close()
        end = time.time()

        execution_time = end - start
        p_api_act = threading.Thread(target=record_api_activity, args=(
            g.user_id, gps_lat, gps_lng, '/v2/stores', str(get_user_ip()), execution_time))
        p_api_act.start()

        print('Execution time (/v2/stores): %s' % (end - start))

        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/v2/stores', error_message)
        return False


@app.route('/v2/set_store_enabled', methods=['POST'])
@app.route('/set_store_enabled', methods=['POST'])
@multi_auth.login_required
def api_set_store_enabled():
    try:
        start = time.time()
        session = Session()
        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' /set_store_enabled:')
        try:
            submission = request.get_json()
        except Exception as e:
            print(e)
            email_crash_report('/set_store_enabled', e)
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

        if 'id' in submission:
            store_id = submission['id']
            store_id = str(store_id)
            store_id = store_id.replace("_", " ")

        else:
            result = '{"status": "missing id : string"}'
            return Response(result, mimetype="application/json")

        if 'is_enabled' in submission:
            is_enabled = submission['is_enabled']
        else:
            result = '{"status": "missing is_enabled : boolean"}'
            return Response(result, mimetype="application/json")

        get_store = session.query(models.stores).filter(
            (models.stores.chain == store_id)
        ).first()
        session.close()

        if get_store:
            chain = get_store.chain
            chain = str(chain)
        else:
            result = '{"invalid id"}'
            return Response(result, mimetype="application/json")

        p_enable = threading.Thread(target=enable_store, args=(g.user_id, chain, is_enabled, False))
        p_enable.start()
        enable_store(g.user_id, chain, is_enabled, True)

        result = '{"status": "updated"}'

        session.close()
        end = time.time()
        execution_time = end - start

        p_api_act = threading.Thread(target=record_api_activity, args=(
            g.user_id, gps_lat, gps_lng, '/set_store_enabled', str(get_user_ip()), execution_time), kwargs={'user_activity': 1})
        p_api_act.start()

        print('Execution time (/set_store_enabled): %s' % (end - start))
        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/set_store_enabled', error_message)
        return False


def enable_store(user_id, chain, enable, is_local):
    if enable is True:
        if is_local is True:
            sql_query = 'delete from user_stores_disabled where user_id = ' + str(user_id) + ' and chain = "' + str(chain) + '"'
        else:
            sql_query = 'delete from user_stores_disabled where user_id = ' + str(user_id) + ' and chain = "' + str(chain) + '"'
        
        session = Session()
        session.execute(sql_query)
        session.commit()
        session.close()

        session_main = Session_main()
        session_main.execute(sql_query)
        session_main.commit()
        session_main.close()

    elif enable is False:
        if is_local is True:
            sql_query = 'insert into user_stores_disabled(user_id, chain) values(' + str(user_id) + ', "' + str(chain) + '")'
        else:
            sql_query = 'insert into user_stores_disabled(user_id, chain, disabled_time) values(' + str(user_id) + ', "' + str(chain) + '", now())'

        session_main = Session_main()
        session_main.execute(sql_query)
        session_main.commit()
        session_main.close()

        session = Session()
        session.execute(sql_query)
        session.commit()
        session.close()
    
    return False


def get_current_store(gps_lat, gps_lng):
    try:

        store_id = 0
        chain = None

        sql_query = 'SELECT id, chain,(select st_distance_sphere(stores.pt, Point(' + gps_lng + ', ' + gps_lat + '))) AS distance FROM stores having distance < 50 ORDER BY distance limit 1'

        session = Session()
        sql_result = session.execute(sql_query)
        session.close()
        if sql_result:
            for row in sql_result:
                store_id = row['id']
                chain = row['chain']
                if store_id == '' or store_id is None:
                    store_id = 0
                    chain = None
        else:
            store_id = 0
            chain = None

        return {'current_store_id': store_id, 'chain': chain}
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('get_current_store', error_message)
        return False

