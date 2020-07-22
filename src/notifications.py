# -*- coding: utf-8 -*-

from __main__ import app
from __main__ import Session
from __main__ import Session_main
from __main__ import g
from __main__ import Response
from __main__ import request
from __main__ import json
from __main__ import models

from src.email import email_crash_report
from src.utils import get_user_ip
from src.utils import check_gps
from src.utils import record_api_activity

from src.stores import get_current_store

import sys
import os
import time
import datetime
import threading

from src.authentication import multi_auth


@app.route('/v2/fcm_token', methods=['POST'])
@app.route('/fcm_token', methods=['POST'])
@multi_auth.login_required
def api_fcm_token():
    try:
        start = time.time()
        try:
            submission = request.get_json()
            print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' /fcm_token')

        except Exception as e:
            print(e)
            email_crash_report('/fm_token', e)

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

        if 'fcm_token' in submission:
            fcm_token = submission['fcm_token']
            if fcm_token is not None:
                fcm_token = fcm_token.strip()
            if fcm_token == '':
                fcm_token = None

        else:
            result = '{"status": "missing fcm_token : string"}'
            print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' ' + result)
            return Response(result, mimetype="application/json")

        if 'os' in submission:
            os_type = submission['os']
            if os_type is not None:
                os_type = os_type.strip()
            if os_type == '':
                os_type = None
        else:
            os_type = None

        session = Session()
        session_main = Session_main()

        if os_type is None:
            os_info = session.query(models.api_activity).filter(
                (models.api_activity.user_id == g.user_id) &
                (models.api_activity.OS is not None)
            ).distinct().order_by(models.api_activity.id.desc()).first()
            session.close()

            if os_info:
                os_type = os_info.OS

        try:
            add_fcm = models.user_fcm(
                user_id=g.user_id,
                fcm_token=fcm_token,
                date_time=datetime.datetime.now(),
                OS=os_type
            )
            session_main.add(add_fcm)
            session_main.commit()
            session_main.close()

            result = '{"status": "fcm_token updated"}'
        except Exception as e:
            print('FCM Already Exists!')
            result = '{"status": "fcm_token ok"}'
            print(e)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)

        end = time.time()

        execution_time = end - start

        p_api_act = threading.Thread(target=record_api_activity, args=(g.user_id, gps_lat, gps_lng, '/fcm_token', str(get_user_ip()), execution_time))
        p_api_act.start()

        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' ' + str(result))
        print('Execution time (/fcm_token): %s' % (end - start))

        return Response(result, mimetype="application/json")

    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/fcm_token', error_message)
        result = '{"status": "fcm_token error"}'
        return Response(result, mimetype="application/json")


@app.route('/v2/open_notification', methods=['POST'])
@app.route('/open_notification', methods=['POST'])
@multi_auth.login_required
def api_notification_opened():
    try:
        start = time.time()
        try:
            submission = request.get_json()

        except Exception as e:
            print(e)
            email_crash_report('/open_notification', e)

            result = '{"status": "MUST BE IN JSON FORMAT"}'
            print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' /open_notification:' + ' ' + result)
            return Response(result, mimetype="application/json")

        if 'gps' in submission:
            gps = submission['gps']
            gps_info = check_gps(gps)
            if gps_info:
                gps_lat = gps_info['gps_lat']
                gps_lng = gps_info['gps_lng']
            else:
                result = '{"status": "GPS Error"}'
                print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(
                    g.user_id) + ' ' + result)
                return Response(result, mimetype="application/json")
        else:
            result = '{"status": "GPS Error"}'
            print(
                str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(
                    g.user_id) + ' ' + result)
            return Response(result, mimetype="application/json")

        if 'notification_id' in submission:
            notification_id = submission['notification_id']
        else:
            result = '{"status": "missing notification_id : string"}'
            print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' ' + result)
            return Response(result, mimetype="application/json")

        sql_str = 'update notifications.notifications set date_time_opened = now() where notifications.notifications.id = "' + str(notification_id) + '"'

        session_main = Session_main()
        session_main.execute(sql_str)
        session_main.commit()
        session_main.close()

        end = time.time()

        result = '{"status": "OK"}'

        execution_time = end - start
        p_api_act = threading.Thread(target=record_api_activity, args=(g.user_id, gps_lat, gps_lng, '/open_notification', str(get_user_ip()), execution_time), kwargs={'user_activity': 1})
        p_api_act.start()

        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' /open_notification')
        print('Execution time (/open_notification): %s' % (end - start))
        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/notification_opened', error_message)
        return False


def record_notification(user_id):
    
    sql_str = 'update notifications.notifications set date_time_opened = now() where notifications.notifications.user_id = "' + str(user_id) + '" and date_time_opened is null and date_time_sent is not null and TIMESTAMPDIFF(hour, date_time_sent, now()) <= 24 limit 1'

    session_main = Session_main()
    session_main.execute(sql_str)
    session_main.commit()
    session_main.close()
    return False
