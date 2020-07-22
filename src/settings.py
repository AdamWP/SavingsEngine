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
import re

from passlib.hash import pbkdf2_sha256

from src.authentication import multi_auth
from src.email import email_crash_report
from src.utils import get_user_ip
from src.utils import check_gps
from src.utils import record_api_activity


@app.route('/v2/change_range', methods=['POST'])
@app.route('/change_range', methods=['POST'])
@multi_auth.login_required
def api_change_range():
    try:
        start = time.time()
        session = Session()
        print(
            str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(
                g.user_id) + ' /change_range:')
        try:
            submission = request.get_json()

        except Exception as e:
            print(e)
            email_crash_report('/change_range', e)

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

        if 'range' in submission:
            range = submission['range']
            range = int(range)
            if range >= 50:
                range = 50
        else:
            result = '{"status": "missing range"}'
            return Response(result, mimetype="application/json")

        p = threading.Thread(target=update_range, args=(g.user_id, range, False))
        p.start()

        update_range(g.user_id, range, True)

        result = '{"status": "range updated"}'

        session.close()

        end = time.time()

        execution_time = end - start
        p_api_act = threading.Thread(target=record_api_activity, args=(
            g.user_id, gps_lat, gps_lng, '/change_range', str(get_user_ip()), execution_time), kwargs={'user_activity': 1})
        p_api_act.start()

        print('Execution time (change_range): %s' % (end - start))
        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/change_range', error_message)
        return False


def update_range(user_id, range, local_db):

    if local_db is True:
        sql_query = 'update user set distance = ' + str(range) + ' where id = ' + str(user_id)
        session = Session()
        session.execute(sql_query)
        session.commit()
        session.close()
    else:
        sql_query = 'update user set distance = ' + str(range) + ' where id = ' + str(user_id)
        session_main = Session_main()
        session_main.execute(sql_query)
        session_main.commit()
        session_main.close()

    return False


@app.route('/v2/profile', methods=['POST'])
@app.route('/profile', methods=['POST'])
@multi_auth.login_required
def api_profile():
    try:
        start = time.time()
        session = Session()

        switches_list_json = []
        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' /profile:')
        try:
            submission = request.get_json()

        except Exception as e:
            print(e)
            email_crash_report('/profile', e)

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

        sql_query = 'select *, (select count(id) from shopping_lists_completed where user_id = user.id) as shopping_lists_completed, (select sum(savings) from user_savings where user_id = user.id) as savings from user where id = "' + str(g.user_id) + '" limit 1'

        query_result = session.execute(sql_query)

        query_result = list(query_result)
        item_info = query_result[0]

        output_record = {}
        if item_info:

            if item_info.username is not None:

                output_record['name'] = None
            else:
                output_record['name'] = None

            if item_info.email is None:
                output_record['email'] = None
                output_record['password'] = False
            else:
                output_record['email'] = item_info.email
                output_record['password'] = True

            if item_info.zip is None:
                output_record['zip'] = None
            else:
                output_record['zip'] = None

            if item_info.points is None:
                output_record['points'] = 0
            else:
                output_record['points'] = item_info.points

            if item_info.points is None:
                output_record['lists_completed'] = 0
            else:
                output_record['lists_completed'] = item_info.shopping_lists_completed

            if item_info.savings is None:
                output_record['savings'] = '$0.00'
            else:
                savings = item_info.savings
                savings = '$' + str(savings)
                output_record['savings'] = savings

            if item_info.share_code is None:
                output_record['share_code'] = None
                output_record['share_url'] = None
            else:
                output_record['share_code'] = item_info.share_code
                output_record['share_url'] = 'https://www.TopSavings.com/share/' + str(item_info.share_code)

            output_record['switches'] = switches_list_json

        result = json.dumps(output_record)

        session.close()

        end = time.time()

        execution_time = end - start
        p_api_act = threading.Thread(target=record_api_activity, args=(
            g.user_id, gps_lat, gps_lng, '/profile', str(get_user_ip()), execution_time))
        p_api_act.start()

        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id))
        print('Execution time (profile): %s' % (end - start))
        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/profile', error_message)
        return False


@app.route('/v2/change_password', methods=['POST'])
@app.route('/change_password', methods=['POST'])
@multi_auth.login_required
def change_password():
    try:
        start = time.time()
        output = []
        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' /change_password:')

        try:
            submission = request.get_json()

        except Exception as e:
            print(e)
            email_crash_report('/change_password', e)

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

        if 'password' in submission:
            password = submission['password']
        else:
            result = '{"status": "missing password : string"}'
            return Response(result, mimetype="application/json")

        if 'password_new' in submission:
            password_new = submission['password_new']
        else:
            result = '{"status": "missing password_new : string"}'
            return Response(result, mimetype="application/json")

        if 'password_new_2' in submission:
            password_new_2 = submission['password_new_2']
        else:
            result = '{"status": "missing password_new_2 : string"}'
            return Response(result, mimetype="application/json")

        session = Session()
        user = session.query(models.user).filter(
            (models.user.id == g.user_id) &
            (models.user.password is not None)
        ).first()
        session.close()

        if user:
            if user.password is not None and user.password != '':
                res = pbkdf2_sha256.verify(password, user.password)
                if res:

                    if not re.match(r'^([a-zA-Z0-9!@#$%^&*]+)$', password_new):
                        status = 'New password may contain letters, numbers, or !@#$%^&*'
                        is_changed = False

                    elif len(password_new) < 6 or len(password_new) > 128:
                        status = 'New password must be 6 - 128 characters long'
                        is_changed = False

                    elif password_new != password_new_2:
                        status = 'New passwords do not match'
                        is_changed = False

                    else:
                        password_new = pbkdf2_sha256.hash(password_new)
                        session_main = Session_main()
                        session_main.query(models.user).filter(
                            (models.user.id == g.user_id)).update(
                            dict(password=password_new))
                        session_main = Session_main()
                        session_main.commit()
                        session_main.close()

                        session.query(models.user).filter(
                            (models.user.id == g.user_id)).update(
                            dict(password=password_new))
                        session.commit()
                        session.close()
                        is_changed = True
                        status = 'Password Changed'

                else:
                    status = 'Invalid Original Password'
                    is_changed = False

            else:
                status = 'Invalid Original Password'
                is_changed = False
        else:
            status = 'Invalid User'
            is_changed = False

        output_record = {}

        output_record['status'] = status
        output_record['is_changed'] = is_changed

        result = json.dumps(output_record)

        end = time.time()

        execution_time = end - start

        p_api_act = threading.Thread(target=record_api_activity, args=(g.user_id, None, None, '/change_password', str(get_user_ip()), execution_time), kwargs={'user_activity': 1})
        p_api_act.start()

        print('Execution time (change_password): %s' % (end - start))
        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/change_password', error_message)
        return False
