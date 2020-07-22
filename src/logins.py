# -*- coding: utf-8 -*-
from __main__ import app
from __main__ import Session
from __main__ import Session_main
from __main__ import g
from __main__ import Response
from __main__ import request
from __main__ import json

from __main__ import jwt


import models
import models_api
import sys
import os
import time
import datetime
import threading
import uuid
import re

import string
import random

from passlib.hash import pbkdf2_sha256

from src.authentication import multi_auth

from src.email import email_crash_report
from src.email import session_alert

from src.email import send_welcome_email
from src.points import add_points

from src.utils import get_user_ip
from src.utils import check_gps
from src.utils import record_api_activity


import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from settings import SMTP_SERVER
from settings import SMTP_PORT
from settings import SMTP_LOGIN
from settings import SMTP_PASSWORD


@app.route('/v2/email_login', methods=['POST'])
@app.route('/email_login', methods=['POST'])
def api_email_login():
    try:
        start = time.time()
        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' /email_login')
        try:
            submission = request.get_json()

        except Exception as e:
            print(e)
            email_crash_report('/email_login', e)
            result = '{"status": "MUST BE IN JSON FORMAT"}'
            return Response(result, mimetype="application/json")

        if 'gps' in submission:
            gps = submission['gps']
            gps_info = check_gps(gps)
            if gps_info:
                gps_lat = gps_info['gps_lat']
                gps_lng = gps_info['gps_lng']
            else:
                result = '{"status": "GPS Error a"}'
                return Response(result, mimetype="application/json")
        else:
            result = '{"status": "GPS Error b"}'
            return Response(result, mimetype="application/json")

        if 'email' in submission:
            email = submission['email']
            if email is not None:
                email = email.strip()
        else:
            result = '{"status": "missing email"}'
            return Response(result, mimetype="application/json")

        if 'password' in submission:
            password = submission['password']
        else:
            result = '{"status": "missing password"}'
            return Response(result, mimetype="application/json")

        session = Session()
        user = session.query(models.user).filter(
            ((models.user.username == email) |
             (models.user.email == email)) &
            (models.user.email is not None) &
            (models.user.email != '')
        ).first()
        session.close()
        if user:
            if user.password is not None:
                res = pbkdf2_sha256.verify(password, user.password)

                if res:
                    g.user_id = user.id
                    g.user_units = user.units
                    token = jwt.dumps({'user_id': g.user_id, 'user_units': g.user_units})
                    output_record = {}
                    output_record['token'] = jwt.dumps(
                        {'user_id': g.user_id, 'units': g.user_units}).decode("utf-8")
                    output_record['prod_id'] = None
                    output_record['search_query'] = None
                    output_record['smart_product'] = None
                    result = json.dumps(output_record)
                    end = time.time()
                    execution_time = end - start
                    print('Execution time (emal_login ): %s' % (execution_time))
                    p_api_act = threading.Thread(target=record_api_activity, args=(g.user_id, gps_lat, gps_lng, '/email_login', str(get_user_ip()), execution_time))
                    p_api_act.start()

                    return Response(result, mimetype="application/json")

                # check to see if user is trying reset password
                if user.password_new != '' and user.password_new is not None:
                    res = pbkdf2_sha256.verify(password, user.password_new)
                    if res:
                        password = pbkdf2_sha256.hash(password)
                        session.query(models.user).filter(
                            (models.user.id == user.id)).update(
                            dict(password=password, password_new=None))
                        #session.commit()
                        #session.close()

                        session.query(models.user).filter(
                            (models.user.id == user.id)).update(
                            dict(password=password, password_new=None))
                        session.commit()
                        session.close()

                        g.user_id = user.id
                        g.user_units = user.units
                        token = jwt.dumps({'user_id': g.user_id, 'user_units': g.user_units})

                        output_record = {}
                        output_record['token'] = jwt.dumps(
                            {'user_id': g.user_id, 'units': g.user_units}).decode("utf-8")
                        output_record['prod_id'] = None
                        output_record['search_query'] = None
                        output_record['smart_product'] = None
                        result = json.dumps(output_record)
                        end = time.time()
                        execution_time = end - start
                        print('Execution time (email_login  ) : %s' % (end - start))
                        p_api_act = threading.Thread(target=record_api_activity, args=(g.user_id, gps_lat, gps_lng, '/email_login', str(get_user_ip()), execution_time))
                        p_api_act.start()

                        return Response(result, mimetype="application/json")

            output_record = {'Invalid Login': 'Invalid Login'}
            result = json.dumps(output_record)
            return Response(result, mimetype="application/json")
            # todo limit number of reset attempts

        else:
            output_record = {'Invalid Login': 'Invalid Login'}
            result = json.dumps(output_record)
            end = time.time()
            execution_time = end - start
            print('Execution time (email_login): %s' % (end - start))
            p_api_act = threading.Thread(target=record_api_activity, args=(
                None, gps_lat, gps_lng, '/email_login', str(get_user_ip()), execution_time))
            p_api_act.start()
            return Response(result, mimetype="application/json")

        output_record = {'Invalid Login': 'Invalid Login'}
        result = json.dumps(output_record)
        end = time.time()
        execution_time = end - start

        p_api_act = threading.Thread(target=record_api_activity, args=(
            g.user_id, gps_lat, gps_lng, '/email_login', str(get_user_ip()), execution_time))
        p_api_act.start()

        print('Execution time (/email_login): %s' % (end - start))
        return Response(result, mimetype="application/json")

    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/email_login', error_message)
        return False


@app.route('/v2/check_username', methods=['POST'])
@app.route('/check_username', methods=['POST'])
def check_username():
    try:
        start = time.time()
        session = Session()
        output_record = {}
        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' /check_username:')
        try:
            submission = request.get_json()

        except Exception as e:
            print(e)
            email_crash_report('/check_username', e)

            result = '{"status": "MUST BE IN JSON FORMAT"}'
            return Response(result, mimetype="application/json")

        user_id = None

        if 'username' in submission:
            username = submission['username']
        else:
            result = '{"status": "missing username"}'
            return Response(result, mimetype="application/json")

        item_info = session.query(models.user).filter(
            (models.user.username == username)).distinct().first()
        session.close()
        if item_info:
            user_id = item_info.id

        if user_id != '' and user_id is not None:
            status_text = username + ' is not available'
            status = 'error'
            is_valid = False
        else:
            if not re.match("^[a-zA-Z0-9_.-]+$", username):
                status_text = 'Username must contain numbers and letters only.'
                status = 'error'
                is_valid = False
            elif len(username) < 5:
                status_text = 'Username must be at least 5 characters long'
                status = 'error'
                is_valid = False
            else:
                status_text = 'Username Available!'
                status = 'available'
                is_valid = True


        output_record['status'] = status
        output_record['status_text'] = status_text
        output_record['is_valid'] = is_valid
        result = json.dumps(output_record)

        # result = {'"status": "' + status + '", "status_text": "' + status_text + '", "is_valid": ' + str(is_valid)}

        end = time.time()
        print('Execution time  (check username): %s' % (end - start))
        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/check_username', error_message)
        return False


@app.route('/v2/check_password', methods=['POST'])
@app.route('/check_password', methods=['POST'])
def check_password():
    try:
        start = time.time()
        output_record = {}
        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' /check_password:')

        try:
            submission = request.get_json()

        except Exception as e:
            print(e)
            email_crash_report('/check_password', e)

            result = '{"status": "MUST BE IN JSON FORMAT"}'
            return Response(result, mimetype="application/json")

        password = None

        if 'password' in submission:
            password = submission['password']
        else:
            result = '{"status": "missing password"}'
            return Response(result, mimetype="application/json")

        if 'password2' in submission:
            password2 = submission['password2']
        else:
            result = '{"status": "missing password2"}'
            return Response(result, mimetype="application/json")

        if not re.match(r'^([a-zA-Z0-9!@#$%^&*:;\'\\()_\-+=|"{}?\/>.<,~`\]\[]+)$', password):

            status = 'Password may contain letters, numbers, or !@#$%^&*'
            is_valid = False

        elif len(password) < 6 or len(password) > 128:

            status = 'Password must be 6 - 128 characters long'
            is_valid = False

        elif password != password2:

            status = 'Passwords do not match'
            is_valid = False

        elif password == password2 and len(password) > 5 and len(password2) > 5:

            status = 'Password OK!'
            is_valid = True


        else:
            status_text = 'unknown error'
            status = 'error'
            is_valid = False

        output_record['status'] = status

        output_record['is_valid'] = is_valid

        result = json.dumps(output_record)

        # result = '[{"status": "' + status + '", "status_text": "' + status_text + '", "status_color": "' + status_color + '", "is_valid": ' + str(is_valid )+ '}]'

        end = time.time()
        print('Execution time (check_password): %s' % (end - start))
        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/check_password', error_message)
        return False


@app.route('/v2/check_email', methods=['POST'])
@app.route('/check_email', methods=['POST'])
def check_email():
    try:
        start = time.time()
        session = Session()
        output_record = {}
        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' /check_email:')

        try:
            submission = request.get_json()

        except Exception as e:
            print(e)
            email_crash_report('/check_email', e)

            result = '{"status": "MUST BE IN JSON FORMAT"}'
            return Response(result, mimetype="application/json")

        user_id = None

        if 'email' in submission:
            email = submission['email']
        else:
            result = '{"status": "missing email"}'
            return Response(result, mimetype="application/json")

        item_info = session.query(models.user).filter(
            (models.user.email == email)).distinct().first()
        session.close()
        if item_info:
            user_id = item_info.id

        if user_id != '' and user_id is not None:
            status_text = email + ' is already registered.'
            status = 'error'
            is_valid = False
        else:
            if not re.match("[^@]+@[^@]+\.[^@]+", email):
                status_text = 'Not a valid email address.'
                is_valid = False
                status = 'error'
            else:
                status_text = 'Email OK!'
                is_valid = True
                status = 'available'

        output_record['status'] = status
        output_record['status_text'] = status_text
        output_record['is_valid'] = is_valid
        result = json.dumps(output_record)

        end = time.time()
        print('Execution time (check_email): %s' % (end - start))
        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/check_email', error_message)
        return False


@app.route('/v2/magic_login', methods=['POST'])
def api_magic_login():
    try:
        start = time.time()
        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' /v2/magic_login')
        try:
            submission = request.get_json()

        except Exception as e:
            print(e)
            email_crash_report('/v2/magic_login', e)
            result = '{"status": "MUST BE IN JSON FORMAT"}'
            return Response(result, mimetype="application/json")

        if 'gps' in submission:
            gps = submission['gps']
            gps_info = check_gps(gps)
            if gps_info:
                gps_lat = gps_info['gps_lat']
                gps_lng = gps_info['gps_lng']
            else:
                result = '{"status": "GPS Error a"}'
                return Response(result, mimetype="application/json")
        else:
            result = '{"status": "GPS Error b"}'
            return Response(result, mimetype="application/json")

        if 'magic_token' in submission:
            magic_token = submission['magic_token']
            if magic_token is not None:
                magic_token = magic_token.strip()
        else:
            result = '{"status": "missing magic_token"}'
            return Response(result, mimetype="application/json")

        session = Session()

        data = jwt.loads(magic_token)
        magic = data['uuid']
        email = data['email']

        str_sql = 'select user.id as user_id, user.units, magic_tokens.magic from user, magic_tokens where user.id = magic_tokens.user_id and user.email = "' + str(email) + '" and magic_tokens.expiry > now() and redeemed_on is null and magic is not null'

        user_info = session.execute(str_sql)
        session.close()

        for row in user_info:
            res = pbkdf2_sha256.verify(magic, row.magic)
            if res:
                
                g.user_id = row.user_id
                g.user_units = row.units
                output_record = {}
                output_record['token'] = jwt.dumps(
                    {'user_id': g.user_id, 'units': g.user_units}).decode("utf-8")
                output_record['prod_id'] = None
                output_record['search_query'] = None
                output_record['smart_product'] = None
                result = json.dumps(output_record)

                # mark magic link as being used
                session.query(models.magic_tokens).filter(
                    (models.magic_tokens.user_id == g.user_id)).update(
                    dict(redeemed_on=datetime.datetime.now(), redeemed_ipaddress=str(get_user_ip())))
                session.commit()
                session.close()

                session_main = Session_main()
                session_main.query(models.magic_tokens).filter(
                    (models.magic_tokens.user_id == g.user_id)).update(
                    dict(redeemed_on=datetime.datetime.now(), redeemed_ipaddress=str(get_user_ip())))
                session_main.commit()
                session_main.close()

                end = time.time()
                execution_time = end - start
                print('Execution time (/v2/magic_login ): %s' % (execution_time))
                p_api_act = threading.Thread(target=record_api_activity, args=(g.user_id, gps_lat, gps_lng, '/v2/magic_login', str(get_user_ip()), execution_time))
                p_api_act.start()

                return Response(result, mimetype="application/json")

        output_record = {'status': 'Invalid magic link b'}
        result = json.dumps(output_record)
        end = time.time()
        execution_time = end - start
        print('Execution time (/v2/magic_login): %s' % (end - start))
        p_api_act = threading.Thread(target=record_api_activity, args=(
            None, gps_lat, gps_lng, '/v2/magic_login', str(get_user_ip()), execution_time))
        p_api_act.start()
        return Response(result, mimetype="application/json")

    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/email_login', error_message)
        return False


@app.route('/v2/onboard_skipped_user', methods=['POST'])
@multi_auth.login_required
def onboard_skipped_user2():
    try:
        start = time.time()
        session = Session()
        session_main = Session_main()

        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' /onboard_skipped_user:')

        try:
            submission = request.get_json()

        except Exception as e:
            print(e)
            email_crash_report('/onboard_skipped_user', e)

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
            if not re.match(r'^([a-zA-Z0-9!@#$%^&*:;\'\\()_\-+=|"{}?\/>.<,~`\]\[]+)$', password):

                output_record = {}
                output_record['token'] = None
                output_record['status'] = 'Password may contain letters, numbers, or !@#$%^&*'
                output_record['is_registered'] = False
                result = json.dumps(output_record)
                return Response(result, mimetype="application/json")

            elif len(password) < 6 or len(password) > 128:
                output_record = {}
                output_record['token'] = None
                output_record['status'] = 'Password must be 6 - 128 characters long'
                output_record['is_registered'] = False
                result = json.dumps(output_record)
                return Response(result, mimetype="application/json")

        else:
            result = '{"status": "missing password"}'
            return Response(result, mimetype="application/json")

        if 'email' in submission:
            email = submission['email']
        else:
            result = '{"status": "missing email"}'
            return Response(result, mimetype="application/json")

        if password != '' and password is not None and email != '' and email is not None:

            item_info = session.query(models.user).filter(
                (models.user.email == email)).distinct().first()
            #session.close()
            if item_info:
                result = '{"status": "email already registered"}'
                return Response(result, mimetype="application/json")

            password = pbkdf2_sha256.hash(password)

            email_unsub_key = str(uuid.uuid4())
            confirmation_key = str(uuid.uuid4())

            sql_query = 'update user set email = "' + email + '", password = "' + password + '", email_unsub_key = "' + email_unsub_key + '", confirmation_key = "' + confirmation_key + '" where id = "' + str(g.user_id) + '"'

            session_main.execute(sql_query)
            session_main.commit()
            session_main.close()

            sql_query = 'update user set email = "' + email + '", password = "' + password + '", email_unsub_key = "' + email_unsub_key + '", confirmation_key = "' + confirmation_key + '" where id = "' + str(g.user_id) + '"'

            session.execute(sql_query)
            session.commit()
            session.close()

            t_welcome_email = threading.Thread(target=send_welcome_email, args=(g.user_id, email, confirmation_key, email_unsub_key))
            t_welcome_email.start()

            output_record = {}
            output_record['token'] = jwt.dumps({'user_id': str(g.user_id), 'units': 'm'}).decode("utf-8")
            output_record['status'] = 'ok'
            output_record['is_registered'] = True

            ipaddress = str(get_user_ip())
            user_share_info = check_user_share(ipaddress)
            prod_id = user_share_info['prod_id']
            is_from_share = user_share_info['is_from_share']

            referral_info = check_referral(ipaddress)
            share_code = referral_info['share_code']
            is_from_referral = referral_info['is_from_referral']

            output_record['prod_id'] = prod_id
            output_record['search_query'] = None
            output_record['smart_product'] = None

            result = json.dumps(output_record)

        else:
            result = '{"status": "email or password error"}'

        end = time.time()

        execution_time = end - start

        p_api_act = threading.Thread(target=record_api_activity, args=(g.user_id, gps_lat, gps_lng, '/v2/onboard_skipped_user', str(get_user_ip()), execution_time))
        p_api_act.start()

        print('Execution time (onboard_skipped_user): %s' % (end - start))
        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/v2/onboard_skipped_userr', error_message)
        return False


@app.route('/v2/new_user', methods=['POST'])
@app.route('/new_user', methods=['POST'])
def new_user():
    try:
        start = time.time()
        session = Session()
        session_main = Session_main()

        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' /new_user:')

        try:
            submission = request.get_json()

        except Exception as e:
            print(e)
            email_crash_report('/new_user', e)

            result = '{"status": "MUST BE IN JSON FORMAT"}'
            return Response(result, mimetype="application/json")

        user_id = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization']
            token = token.replace('Bearer ', '')

            try:
                data = jwt.loads(token)
                user_id = data['user_id']
            except:
                user_id = None

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

        if 'first_name' in submission:
            first_name = submission['first_name']
            if first_name is not None:
                first_name = first_name.strip()
            if first_name == '':
                first_name = None
        else:
            first_name = None

        if 'last_name' in submission:
            last_name = submission['last_name']
            if last_name is not None:
                last_name = last_name.strip()
            if last_name == '':
                last_name = None
        else:
            last_name = None

        if 'username' in submission:
            username = submission['username']
            if username is not None:
                username = username.strip()
            if username == '':
                username = None
        else:
            username = None

        if 'password' in submission:
            password = submission['password']
            if not re.match(r'^([a-zA-Z0-9!@#$%^&*:;\'\\()_\-+=|"{}?\/>.<,~`\]\[]+)$', password):

                output_record = {}
                output_record['token'] = None
                output_record['status'] = 'Password may contain letters, numbers, or !@#$%^&*'
                output_record['is_registered'] = False
                result = json.dumps(output_record)
                return Response(result, mimetype="application/json")

            elif len(password) < 6 or len(password) > 128:

                output_record = {}
                output_record['token'] = None
                output_record['status'] = 'Password must be 6 - 128 characters long'
                output_record['is_registered'] = False
                result = json.dumps(output_record)
                return Response(result, mimetype="application/json")

        else:
            result = '{"status": "missing password"}'
            return Response(result, mimetype="application/json")

        if 'email' in submission:
            email = submission['email']
        else:
            result = '{"status": "missing email"}'
            return Response(result, mimetype="application/json")

        if password != '' and password is not None and email != '' and email is not None:

            item_info = session.query(models.user).filter(
                (models.user.email == email)
            ).distinct().first()
            session.close()
            if item_info:

                result = '{"status": "already registered"}'
                return Response(result, mimetype="application/json")

            password = pbkdf2_sha256.hash(password)

            share_code = get_share_code()

            store_count = get_store_count(gps_lat, gps_lng, 10000)

            if store_count > 10:
                distance = 10

            else:
                store_count = get_store_count(gps_lat, gps_lng, 25000)

                if store_count > 10:
                    distance = 25

                else:
                    distance = 50

            email_unsub_key = str(uuid.uuid4())
            confirmation_key = str(uuid.uuid4())

            session_start = datetime.datetime.now()

            if user_id is None:
                add_newuser = models.user(
                    join_date=session_start,
                    password=password,
                    email=email,
                    gps_lat=gps_lat,
                    gps_lng=gps_lng,
                    savings='0.00',
                    points='0',
                    units='m',
                    distance=distance,
                    share_code=share_code,
                    email_unsub_key=email_unsub_key,
                    confirmation_key=confirmation_key,
                    last_session_start=session_start

                )
                session_main.add(add_newuser)
                session_main.commit()
                user_id = add_newuser.id
                g.user_id = user_id
                session_main.close()

                add_newuser = models.user(
                    id=user_id,
                    join_date=session_start,
                    password=password,
                    email=email,
                    gps_lat=gps_lat,
                    gps_lng=gps_lng,
                    savings='0.00',
                    points='0',
                    units='m',
                    distance=distance,
                    share_code=share_code,
                    email_unsub_key=email_unsub_key,
                    confirmation_key=confirmation_key,
                    last_session_start=session_start

                )
                session.add(add_newuser)
                session.commit()
                session.close()

                t_welcome_email = threading.Thread(target=send_welcome_email, args=(g.user_id, email, confirmation_key, email_unsub_key))
                t_welcome_email.start()

            else:

                session_main.query(models.user).filter(
                    (models.user.id == user_id)).update({'email': email, 'password': password})
                session_main.commit()
                session_main.close()

                session.query(models.user).filter(
                    (models.user.id == user_id)).update({'email': email, 'password': password})
                session.commit()
                session.close()

            units = 'm'
            output_record = {}
            output_record['token'] = jwt.dumps({'user_id': user_id, 'units': units}).decode("utf-8")
            output_record['status'] = 'ok'
            output_record['is_registered'] = True

            ipaddress = str(get_user_ip())
            user_share_info = check_user_share(ipaddress)
            prod_id = user_share_info['prod_id']
            smart_product = user_share_info['smart_product']
            search_query = user_share_info['search_query']
            deal_category = user_share_info['deal_category']

            is_from_share = user_share_info['is_from_share']

            referral_info = check_referral(ipaddress)
            share_code = referral_info['share_code']
            is_from_referral = referral_info['is_from_referral']

            if prod_id is None and smart_product is None and search_query is None and deal_category is None:
                prod_id = referral_info['prod_id']
                smart_product = referral_info['smart_product']
                search_query = referral_info['search_query']
                deal_category = referral_info['deal_category']

            output_record['prod_id'] = prod_id
            output_record['smart_product'] = smart_product
            output_record['search_query'] = search_query
            output_record['deal_category'] = deal_category

            result = json.dumps(output_record)

            if is_from_share is not None:
                p_email_subject = '❇️:OS:📧📲 New TopSavings Email User(via share)'
                p_email_text = ':OS: User ' + str(g.user_id) + ' via share and signed up with an email address.  \r\n  \r\n  Shared Deal:   https://www.topsavings.com/deals/deal_' + str(is_from_share) + '  \r\n  \r\n  Install Location: https://www.google.com/maps/place/' + str(gps_lat) + ',' + str(gps_lng)

            elif share_code is not None and share_code != '':
                p_email_subject = '❇️:OS:📧 New TopSavings Email User (via ' + str(share_code) + ')'
                p_email_text = ':OS: User ' + str(g.user_id) + ' referred from ' + str(share_code) + ' signed up with an email address.   \r\n  \r\n  Install Location:  https://www.google.com/maps/place/' + str(gps_lat) + ',' + str(gps_lng)

            else:
                p_email_subject = '❇️:OS:📧 New TopSavings Email User'
                p_email_text = ':OS: User ' + str(g.user_id) + ' signed up with an email address.   \r\n  \r\n  Install Location:  https://www.google.com/maps/place/' + str(gps_lat) + ',' + str(gps_lng)

            if gps_lat == '45.414926' and gps_lng == '-75.696562':
                p_email_subject = p_email_subject + ' GPS PROBLEM'

            p_session_alert = threading.Thread(target=session_alert, args=(g.user_id, session_start, None, 'New User', None, is_from_share, share_code))
            p_session_alert.start()

        else:
            result = '{"status": "email or password error"}'

        end = time.time()
        execution_time = end - start

        p_api_act = threading.Thread(target=record_api_activity, args=(
            g.user_id, gps_lat, gps_lng, '/new_user', str(get_user_ip()), execution_time))
        p_api_act.start()

        print('Execution time (new_user): %s' % (end - start))
        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/new_user', error_message)
        return False


@app.route('/v2/reset_password', methods=['POST'])
@app.route('/reset_password', methods=['POST'])
def reset_password():

    try:
        start = time.time()

        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' /reset_password:')

        try:
            submission = request.get_json()
        except Exception as e:
            print(e)
            email_crash_report('/reset_password', e)

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

        if 'email' in submission:
            email = submission['email']
        else:
            result = '{"status": "missing email"}'
            return Response(result, mimetype="application/json")

        session = Session()
        user = session.query(models.user).filter(
            (models.user.email == email)  &
            (models.user.email is not None)
        ).first()
        session.close()

        if user:
            password = ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(8))

            email = user.email

            password_new = pbkdf2_sha256.hash(password)

            session_main = Session_main()
            session_main.query(models.user).filter(
                (models.user.id == user.id)).update(
                dict(password_new=password_new))
            session_main.commit()
            session_main.close()

            session.query(models.user).filter(
                (models.user.id == user.id)).update(
                dict(password_new=password_new))
            session.commit()
            session.close()
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(SMTP_LOGIN, SMTP_PASSWORD)

            TEXT = 'Your TopSavings mobile app password has been reset.\n\n Your new password is ' + password + '\n\n If you did not reset your password you can ignore this message and your old password will still work. \n\n Your password may be changed from the Settings > Profile screen in the TopSavings app.'
            SUBJECT = 'TopSavings Password Reset'
            msg = 'Subject: {}\n\n{}'.format(SUBJECT, TEXT)

            server.sendmail("mailer@TopSavings.com", email, msg)
            server.quit()

            output_record = {}
            output_record['status_text'] = 'OK!'
            output_record['status'] = 'ok'
            output_record['is_valid'] = True

            result = json.dumps(output_record)

            end = time.time()
            print('Execution time (reset_password 1): %s' % (end - start))
            return Response(result, mimetype="application/json")

        output_record = {}
        output_record['status_text'] = 'Invalid Email (+_+)'
        output_record['status'] = 'error'
        output_record['is_valid'] = False

        result = json.dumps(output_record)

        end = time.time()
        execution_time = end - start

        p_api_act = threading.Thread(target=record_api_activity, args=(
            g.user_id, gps_lat, gps_lng, 'reset_password', str(get_user_ip()), execution_time))
        p_api_act.start()

        print('Execution time (reset_password): %s' % (end - start))
        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/reset_password', error_message)
        return False


@app.route('/v2/reset_password_magic', methods=['POST'])
def reset_password_magic():

    try:
        start = time.time()

        ipaddress = str(get_user_ip())

        print(str(datetime.datetime.now()) + ' IP:' + ipaddress + ' /v2/reset_password_magic:')

        try:
            submission = request.get_json()
        except Exception as e:
            print(e)
            email_crash_report('/v2/reset_password_magic', e)

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

        if 'email' in submission:
            email = submission['email']
        else:
            result = '{"status": "missing email"}'
            return Response(result, mimetype="application/json")

        session = Session()
        user = session.query(models.user).filter(
            (models.user.email == email) &
            (models.user.email is not None)
        ).first()
        session.close()

        expiration = datetime.datetime.now() + datetime.timedelta(minutes=15)
        expiration = str(expiration)

        if user:
            user_id = user.id
            magic = pbkdf2_sha256.hash(str(uuid.uuid4()))
            magic_token = jwt.dumps({"email": email, 'ipaddress': ipaddress, 'expiration': expiration,'uuid': magic}).decode("utf-8")

            magic_encrypted = pbkdf2_sha256.hash(magic)
            add_magic_link = models.magic_tokens(
                user_id=user_id,
                magic=magic_encrypted,
                expiry=expiration,
                ipaddress=ipaddress
            )
            session_main = Session_main()
            session_main.add(add_magic_link )
            session_main.commit()
            session_main.close()

            add_magic_link = models_api.magic_tokens(
                user_id=user_id,
                magic=magic_encrypted,
                expiry=expiration,
                ipaddress=ipaddress
            )

            session.add(add_magic_link)
            session.commit()
            session.close()

            TEXT = 'You told us you forgot your password. If you really did, click here to choose a new one. \n\n https://www.topsavings.com/reset/' + str(magic_token) + '  \n\n If you didn\'t mean to reset your password, then you can just ignore this email; your password will not change.  \n\n\n Link not working? Just copy and paste this link in your browser.  https://www.topsavings.com/reset/' + str(magic_token) + ' \n\n\n\n '

            msg = MIMEMultipart('alternative')
            msg['From'] = 'TopSavings <mailer@TopSavings.com>'
            msg['To'] = email

            part1 = MIMEText(TEXT, 'plain')
            msg.attach(part1)

            """if alert_html is not None:
                part2 = MIMEText(alert_html, 'html')
                msg.attach(part2)"""

            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.ehlo()
            server.starttls()
            server.login(SMTP_LOGIN, SMTP_PASSWORD)

            msg['Subject'] = 'TopSavings Password Reset'
            server.sendmail("mailer@TopSavings.com", email, msg.as_string())
            server.quit()

            output_record = {}
            output_record['status_text'] = 'Please check your email for login information.'
            output_record['status'] = 'Please check your email for login information.'
            output_record['is_valid'] = True

            result = json.dumps(output_record)

            end = time.time()
            execution_time = end - start

            p_api_act = threading.Thread(target=record_api_activity, args=(g.user_id, gps_lat, gps_lng, '/v2/reset_password_magic', str(get_user_ip()), execution_time))
            p_api_act.start()

            print('Execution time (/v2/reset_password_magic): %s' % (end - start))
            return Response(result, mimetype="application/json")

        output_record = {}
        output_record['status_text'] = 'Invalid Email'
        output_record['status'] = 'Invalid Email'
        output_record['is_valid'] = False

        result = json.dumps(output_record)

        end = time.time()
        execution_time = end - start

        p_api_act = threading.Thread(target=record_api_activity, args=(
            g.user_id, gps_lat, gps_lng, '/v2/reset_password_magic', str(get_user_ip()), execution_time))
        p_api_act.start()

        print('Execution time (/v2/reset_password_magic): %s' % (end - start))
        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/v2/reset_password', error_message)
        return False


@app.route('/v2/skip_login', methods=['POST'])
@app.route('/skip_login', methods=['POST'])
def api_skip_login():
    try:
        start = time.time()
        session = Session()
        session_main = Session_main()

        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' /skip_login:')

        try:
            submission = request.get_json()

        except Exception as e:
            print(e)
            email_crash_report('/skip_login', e)

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

        share_code = get_share_code()

        store_count = get_store_count(gps_lat, gps_lng, 10000)

        if store_count > 10:
            distance = 10

        else:
            store_count = get_store_count(gps_lat, gps_lng, 25000)

            if store_count > 10:
                distance = 25

            else:
                distance = 50

        # todo calculate distance based on # stores inside area

        session_start = datetime.datetime.now()
        add_newuser = models.user(
            join_date=session_start,
            gps_lat=gps_lat,
            gps_lng=gps_lng,
            savings='0.00',
            points='0',
            units='m',
            distance=distance,
            share_code=share_code,
            last_session_start=session_start
        )
        session_main.add(add_newuser)
        session_main.commit()
        user_id = add_newuser.id
        g.user_id = user_id
        session_main.close()

        add_newuser = models_api.user(
            id=user_id,
            join_date=session_start,
            gps_lat=gps_lat,
            gps_lng=gps_lng,
            savings='0.00',
            points='0',
            units='m',
            distance=distance,
            share_code=share_code,
            last_session_start=session_start
        )
        session.add(add_newuser)
        session.commit()
        session.close()

        units = 'm'
        output_record = {}
        output_record['token'] = jwt.dumps({'user_id': user_id, 'units': units}).decode("utf-8")

        ipaddress = str(get_user_ip())

        user_share_info = check_user_share(ipaddress)
        prod_id = user_share_info['prod_id']
        smart_product = user_share_info['smart_product']
        search_query = user_share_info['search_query']
        deal_category = user_share_info['deal_category']

        is_from_share = user_share_info['is_from_share']

        referral_info = check_referral(ipaddress)
        share_code = referral_info['share_code']

        if prod_id is None and smart_product is None and search_query is None and deal_category is None:
            prod_id = referral_info['prod_id']
            smart_product = referral_info['smart_product']
            search_query = referral_info['search_query']
            deal_category = referral_info['deal_category']

        output_record['prod_id'] = prod_id
        output_record['smart_product'] = smart_product
        output_record['search_query'] = search_query
        output_record['deal_category'] = deal_category

        result = json.dumps(output_record)

        p_session_alert = threading.Thread(target=session_alert, args=(g.user_id, session_start, None, 'Skipped User', None, is_from_share, share_code))
        p_session_alert.start()

        end = time.time()
        execution_time = end - start

        p_api_act = threading.Thread(target=record_api_activity, args=(g.user_id, gps_lat, gps_lng, '/skip_login', str(get_user_ip()), execution_time))
        p_api_act.start()

        print('Execution time (/skip_login): %s' % (end - start))
        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/skip_login', error_message)
        return False


def get_share_code():

    share_code = None
    BASE_LIST = string.digits + string.ascii_letters

    i = 0
    while i < 10:

        share_code = ''.join(random.choice(string.ascii_uppercase ) for char in range(2))

        share_code = share_code + ''.join(random.choice(string.digits))

        share_code = share_code + ''.join(random.choice(string.ascii_uppercase) for char in range(3))

        share_code = share_code + ''.join(random.choice(string.digits))

        str_sql = 'select share_code from user where share_code = "' + str(share_code) + '"'
        session = Session()
        item_info = session.execute(str_sql)
        session.close()

        old_share_code = None

        for row in item_info:
            old_share_code = row.share_code

        if old_share_code is None:
            i = 10
        else:
            i = i + 1

    return share_code


def get_store_count(gps_lat, gps_lng, distance):

    str_sql = 'select count(id) as store_count from stores where (select st_distance_sphere(stores.pt, Point(' + str(gps_lng) + ', ' + str(gps_lat) + '))) <= ' + str(distance) + ' and id > 100 '

    session = Session()
    store_count_results = session.execute(str_sql)
    session.close()

    store_count = 0
    for row in store_count_results:
        store_count = row.store_count

    return store_count


def check_referral(ipaddress):

    session_main = Session_main()

    str_sql = 'select referrals.id, referrals.share_code, deals_shared.prod_id, deals_shared.smart_product, deals_shared.search_query, deals_shared.deal_category, (select id from user where share_code = referrals.share_code) as user_id from referrals, deals_shared where referrals.ipaddress = "' + ipaddress + '" and TIMESTAMPDIFF(MINUTE, referrals.date_time, now()) < 1440 and referrals.user_id is null and referrals.share_code is not null and referrals.share_code = deals_shared.deal_id order by referrals.id desc limit 1'

    referral = session_main.execute(str_sql)
    session_main.close()
    referral = list(referral)

    share_code = None
    is_from_referral = False
    referrals_id = None
    shared_user_id = None
    prod_id = None
    smart_product = None
    search_query = None
    deal_category = None

    if len(referral) > 0:
        for row in referral:

            if row.prod_id is None:
                prod_id = None
            else:
                prod_id = row.prod_id

            if row.smart_product is None:
                smart_product = None
            else:
                smart_product = row.smart_product

            if row.search_query is None:
                search_query = None
            else:
                search_query = row.search_query

            if row.deal_category is None:
                deal_category = None
            else:
                deal_category = row.deal_category

            if row.id is None:
                referrals_id = None
            else:
                referrals_id = row.id

            if row.share_code is None:
                share_code = None
            else:
                share_code = row.share_code

            if row.user_id is None:
                shared_user_id = None
            else:
                shared_user_id = row.user_id
        if referrals_id is not None:
            str_sql = 'update referrals set user_id = "' + str(g.user_id) + '" where id = ' + str(referrals_id)

            session_main.execute(str_sql)
            session_main.commit()
            session_main.close()
            is_from_referral = True

        if shared_user_id is not None and referrals_id is not None:

            add_points(shared_user_id, 50, 'new_user_share_code', None, None, None, referrals_id)

        else:
            print('NO REFERRAL')

    return {'prod_id': prod_id, 'smart_product': smart_product, 'search_query': search_query, 'deal_category': deal_category, 'share_code': share_code, 'is_from_referral': is_from_referral}


def check_user_share(ipaddress):
    # todo track performance

    # todo deals_shared should be shared_id's not deals_id
    session_main = Session_main()
    sql_query = 'select deals_shared.user_id, deals_shared.prod_id, deals_shared.smart_product, deals_shared.search_query, deals_shared.deal_category, deals_shared_opened.id, deals_shared_opened.share_id from deals_shared, deals_shared_opened where deals_shared.deal_id = deals_shared_opened.share_id and ipaddress = "' + ipaddress + '" and TIMESTAMPDIFF(MINUTE, deals_shared_opened.date_time, now()) < 1440 and deals_shared_opened.user_id is null order by deals_shared_opened.id desc limit 1'

    share_info = session_main.execute(sql_query)
    session_main.close()
    share_info = list(share_info)

    prod_id = None
    is_from_share = None
    smart_product = None
    search_query = None
    deal_category = None

    if share_info:
        for row in share_info:
            if row.prod_id is None:
                prod_id = None
            else:
                prod_id = row.prod_id

            if row.smart_product is None:
                smart_product = None
            else:
                smart_product = row.smart_product

            if row.search_query is None:
                search_query = None
            else:
                search_query = row.search_query

            if row.deal_category is None:
                deal_category = None
            else:
                deal_category = row.deal_category

            if row.user_id is None:
                deals_shared_user_id = None
            else:
                deals_shared_user_id = row.user_id

            if row.id is None:
                deals_shared_opened_id = None
            else:
                deals_shared_opened_id = row.id

            if row.id is not None:
                is_from_share = row.share_id
                share_opened_id = row.id
                str_sql = 'update deals_shared_opened set user_id = "' + str(g.user_id) + '" where id = ' + str(share_opened_id)

                session_main.execute(str_sql)
                session_main.commit()
                session_main.close()

                if deals_shared_user_id is not None and deals_shared_opened_id is not None:
                    add_points(deals_shared_user_id, 50, 'new_user_deal_shared', None, None, deals_shared_opened_id, None)

    return {'prod_id': prod_id, 'smart_product': smart_product, 'search_query': search_query, 'deal_category': deal_category, 'is_from_share': is_from_share}