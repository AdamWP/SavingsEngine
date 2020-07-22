# -*- coding: utf-8 -*-

from __main__ import Session
from __main__ import Session_main
from __main__ import g
from __main__ import request
from __main__ import jwt
from __main__ import models

import sys
import os
import time
import datetime
import threading

from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth, MultiAuth

from src.email import session_alert
from src.email import email_crash_report

basic_auth = HTTPBasicAuth()
token_auth = HTTPTokenAuth('Bearer')
multi_auth = MultiAuth(basic_auth, token_auth)


@basic_auth.verify_password
def verify(username, password):
    start = time.time()
    session = Session()

    user = session.query(models.user).filter(models.user.username == username).first()
    g.username = username
    if user:
        res = pbkdf2_sha256.verify(password, user.password)
        if res:
            g.user_id = user.id
            g.user_units = user.units
            token = jwt.dumps({'user_id': g.user_id, 'user_units': g.user_units})
    else:
        res = False
    session.close()
    return res


@token_auth.verify_token
def verify_token(token):
    try:
        last_session_start = None
        try:
            data = jwt.loads(token)

        except Exception as e:
            print(e)
            email_crash_report('/verify_token', e)
            return False

        if 'user_id' in data:

            g.user_id = data['user_id']
            if 'units' in data:
                g.user_units = data['units']
            else:
                g.user_units = 'm'

            session = Session()

            sql_query = 'select * from user where disabled is null and id = ' + str(g.user_id) + ' order by id limit 1'

            user_info = session.execute(sql_query)
            session.close()

            for row in user_info:
                if row.id is None or row.id == '':
                    return False
                else:

                    g.app_version = row.app_version
                    os_type = row.OS
                    zone_id = row.zone_id
                    last_session_start = row.last_session_start

                    if row.admin is not None:
                        g.admin = True
                    else:
                        g.admin = False

                    if row.distance is not None and row.distance != '':
                        distance = row.distance
                        distance = distance * 1000
                        g.distance = distance
                    else:
                        g.distance = 10000

                    if row.content_moderator == 1:
                        g.content_moderator = True
                    else:
                        g.content_moderator = False

                    g.zone_id = zone_id
             
            if request.path == '/v2/check_in':
                return True

            if last_session_start is None:
                time_diff_hours = 0
            else:
                now = datetime.datetime.now()

                time_diff = now - last_session_start

                time_diff_hours = (time_diff.days * 24) + (time_diff.seconds / 3600)
                if time_diff_hours > 24:
                    time_diff_disp = str(time_diff.days) + ' days'
                else:
                    time_diff_hours = round(time_diff_hours,2)
                    time_diff_disp = str(time_diff_hours) + ' hours'
                                       
            if time_diff_hours > 1:

                session_start = datetime.datetime.now()

                session.query(models.user).filter(
                    (models.user.id == g.user_id)).update(
                    dict(last_session_start=str(session_start)))
                session.commit()
                session.close()

            if time_diff_hours > 1 and g.admin is False and g.content_moderator is False:
                user_type = 'Return User'
                p_session_alert = threading.Thread(target= session_alert, args=(g.user_id, session_start, os_type, user_type, time_diff_disp, None, None))
                p_session_alert.start()

            return True

        else:
            return False

    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/verify_token', error_message)
        return False
