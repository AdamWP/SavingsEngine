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

from src.authentication import multi_auth
from src.email import email_crash_report
from src.notifications import record_notification
from src.utils import get_user_ip
from src.utils import check_gps
from src.utils import record_api_activity

from src.email import session_alert

from settings import APP_VERSION_iOS
from settings import APP_VERSION_ANDROID

APP_VERSION_iOS = int(APP_VERSION_iOS)
APP_VERSION_ANDROID = int(APP_VERSION_ANDROID)


@app.route('/v2/startup_check', methods=['POST'])
@app.route('/startup_check', methods=['POST'])
@multi_auth.login_required
def api_startup_check():
    try:
        start = time.time()

        try:

            submission = request.get_json()
            print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' /startup_check:' + str(submission))

        except Exception as e:
            print(e)
            email_crash_report('/startup_check', e)

            result = '{"status": "MUST BE IN JSON FORMAT"}'
            print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' /startup_check:' + ' ' + result)
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

        if 'version' in submission:
            version = submission['version']
            if version == '' or version is None:
                version = None
            else:
                version = int(version)
        else:
            result = '{"status": "missing version : string"}'
            print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' ' + result)
            return Response(result, mimetype="application/json")

        if 'os' in submission:
            os_check = submission['os']
            if os_check is not None:
                os_check = os_check.strip()
            if os_check == '' or os_check is None:
                os_check = None
        else:
            result = '{"status": "missing os : string"}'
            print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' ' + result)
            return Response(result, mimetype="application/json")

        if 'device' in submission:
            device = submission['device']
            if device is not None:
                device = device.strip()
            if device == '':
                device = None

        else:
            result = '{"status": "missing device : string"}'
            print(
                str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' ' + result)
            return Response(result, mimetype="application/json")

        if 'location_services' in submission:
            location_services = submission['location_services']
            if location_services is not None:
                location_services = location_services.strip()
            if location_services == '':
                location_services = None
        else:
            result = '{"status": "missing location_services : string"}'
            print(
                str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' ' + result)
            return Response(result, mimetype="application/json")

        if 'notifications' in submission:
            notifications = submission['notifications']
            if notifications is not None:
                notifications = notifications.strip()
            if notifications == '':
                notifications = None

        else:
            result = '{"status": "missing notifications : string"}'
            print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' ' + result)
            return Response(result, mimetype="application/json")

        result = {}

        if version < (APP_VERSION_ANDROID - 5) and os_check == 'Android' and g.notification_opened is False:
            result['needsUpdate'] = True
            result['message'] = 'Update recommended. Upgrade for free with Google Play.'
        elif version < (APP_VERSION_iOS - 5) and os_check == 'iOS':
            result['needsUpdate'] = True
            result['message'] = 'Upgrade recommended. Upgrade for free in the App Store.'
        else:
            result['needsUpdate'] = False
            result['message'] = None

        str_sql = 'select id as store_count, (select id from (select *, st_distance_sphere(Point(gps_lng, gps_lat), Point(' + gps_lng + ', ' + gps_lat + ')) as distance from deals.zones order by distance limit 1)t1) as zone_id from stores where (select st_distance_sphere(stores.pt, Point(' + gps_lng + ', ' + gps_lat + '))) <= 50000 and id > 100 limit 1'

        session = Session()
        session_main = Session_main()

        store_count_results = session.execute(str_sql)
        session.close()

        store_count = 0
        zone_id = 1
        for row in store_count_results:
            store_count = row.store_count
            zone_id = row.zone_id

        if store_count > 0:
            result['in_available_area'] = True
        else:
            result['in_available_area'] = False

        result['show_deals'] = True
        result['deals_category'] = None
        result['store_chain'] = None
        result['prod_id'] = None
        result['search_query'] = None
        result['smart_product'] = None
        result['start_screen'] = 'deals'
        result['tab_order'] = ['deals', 'shopping_list', 'price_check', 'search', 'profile']

        result = json.dumps(result)

        session_start = datetime.datetime.now()

        session.query(models.user).filter(
            (models.user.id == g.user_id)).update(
            dict(last_session_start=str(session_start), device=device, location_services=location_services, OS=os_check, app_version=str(version), zone_id=str(zone_id)))

        session.commit()
        session.close()

        session_main.query(models.user).filter(
            (models.user.id == g.user_id)).update(
            dict(last_session_start=str(session_start), device=device,
                 location_services=location_services, OS=os_check, app_version=str(version), zone_id=str(zone_id)))

        session_main.commit()
        session_main.close()

        p_noti = threading.Thread(target=record_notification, args=(g.user_id,))
        p_noti.start()

        end = time.time()
        execution_time = end - start

        p_api_act = threading.Thread(target=record_api_activity,args=(g.user_id, gps_lat, gps_lng, '/startup_check', str(get_user_ip()), execution_time), kwargs={'os_type': os_check})
        p_api_act.start()

        end = time.time()

        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' ' + str(result))
        print('Execution time (/startup_check): %s' % (end - start))
        return Response(result, mimetype="application/json")

    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/startup_check', error_message)
        result = {}
        result['needsUpdate'] = False
        result['message'] = None
        result['in_available_area'] = True
        result['show_deals'] = False
        result['deals_category'] = None
        result['store_chain'] = None
        result['prod_id'] = None
        result['search_query'] = None
        result['smart_product'] = None
        result['status'] = 'something went wrong'
        result['start_screen'] = 'deals'
        result['tab_order'] = ['deals', 'shopping_list', 'price_check', 'search', 'profile']

        return Response(result, mimetype="application/json")
