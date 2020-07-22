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
import uuid

from src.authentication import multi_auth
from src.email import email_crash_report
from src.utils import get_user_ip
from src.utils import check_gps
from src.utils import record_api_activity


@app.route('/v2/redeem_points_token', methods=['POST'])
@app.route('/redeem_points_token', methods=['POST'])
@multi_auth.login_required
def api_redeem_points_token():
    try:
        start = time.time()
        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(
            g.user_id) + ' /redeem_points_token:')

        try:
            submission = request.get_json()
        except Exception as e:
            print(e)
            email_crash_report('/redeem_points_token', e)

            result = '{"status": "MUST BE IN JSON FORMAT"}'
            return Response(result, mimetype="application/json")

        if 'points_token' in submission:
            points_token = submission['points_token']
            points_info = redeem_points_token(points_token, None)
            points = points_info['points']
            points_message = points_info['points_message']
        else:
            result = {"missing points_token : string"}
            return Response(result, mimetype="application/json")

        end = time.time()

        execution_time = end - start

        p_api_act = threading.Thread(target=record_api_activity, args=(g.user_id, None, None, '/redeem_points_token', None, execution_time))
        p_api_act.start()

        print('Execution time (/redeem_points_token): %s' % (end - start))
        return json.dumps({'points': points, 'points_message': points_message})
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/redeem_points_token', error_message)
        return False


def get_points_token(reward_type, scan_id, prod_id):
    try:
        points_reward = None
        points_token = None

        session_main = Session_main()

        session = Session()

        since = datetime.datetime.now() - datetime.timedelta(hours=24)

        if reward_type == 'take_product_picture' and scan_id != '' and scan_id is not None:

            # make sure token hasn't been submitted for this scan already
            check_recent = session_main.query(models.points).filter(
                (models.points.scan_id == scan_id) &
                (models.points.user_id == g.user_id) &
                (models.points.reward_type == 'take_product_picture')
            ).distinct().count()
            session_main.close()

            if check_recent < 1:
                points_reward = 50
                points_token = str(uuid.uuid4())

                submission = models.points(
                    user_id=int(g.user_id),
                    points=points_reward,
                    reward_type=str(reward_type),
                    token=points_token,
                    scan_id=scan_id,
                    offered_on=datetime.datetime.utcnow()
                )
                session_main.add(submission)
                session_main.commit()
        elif reward_type == 'add_to_list' and prod_id != '' and prod_id != None:
            # check if points have been given for adding to list in past 24 hours or if item has been in list in past 24 hours

            check_recent = session_main.query(models.points).filter(
                (models.points.prod_id == prod_id) &
                (models.points.user_id == g.user_id) &
                (models.points.reward_type == 'add_to_list') &
                (models.points.offered_on > since)
            ).distinct().count()

            if check_recent < 1:
                points_reward = 1
                points_token = str(uuid.uuid4())
                submission = models.points(
                    user_id=int(g.user_id),
                    points=points_reward,
                    reward_type=str(reward_type),
                    token=points_token,
                    scan_id=scan_id,
                    prod_id=prod_id,
                    offered_on=datetime.datetime.utcnow()
                )
                session_main.add(submission)
                session_main.commit()
                session_main.close()
            else:
                get_recent = session_main.query(models.points).filter(
                    (models.points.prod_id == prod_id) &
                    (models.points.user_id == g.user_id) &
                    (models.points.reward_type == 'add_to_list') &
                    (models.points.earned_on is None) &
                    (models.points.offered_on > since)

                ).first()
                session_main.close()

                if get_recent:
                    points_reward = get_recent.points
                    points_token = get_recent.token

        return {'points_reward': points_reward, 'points_token': points_token}
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('get_points_token', error_message)
        return False


def redeem_points_token(points_token, prod_id):
    try:
        session_main = Session_main()
        session = Session()

        points = None
        points_message = None
        check_points_token = session_main.query(models.points).filter(
            (models.points.token == points_token) &
            (models.points.prod_id == prod_id) &
            (models.points.user_id == g.user_id) &
            (models.points.earned_on is None)
        ).distinct().first()
        session_main.close()

        if check_points_token:
            points = check_points_token.points
            points_id = check_points_token.id
            reward_type = check_points_token.reward_type
            if reward_type == 'add_to_list':
                points_message = 'Item Added to Shopping List!'
            elif reward_type == 'take_product_picture':
                points_message = 'Picture Submitted'

            session_main.query(models.points).filter(
                (models.points.id == points_id)).update(
                dict(earned_on=datetime.datetime.now()))
            session_main.commit()
            session_main.close()

            sql_query = 'update user set points = points + ' + str(points) + ' where id = ' + str(g.user_id)

            session_main.execute(sql_query)
            session_main.commit()
            session_main.close()

            sql_query = 'update user set points = points + ' + str(points) + ' where id = ' + str(g.user_id)
            session.execute(sql_query)
            session.commit()
            session.close()

        return {'points': points, 'points_message': points_message}
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('redeem_points_token', error_message)
        return False


def add_points(user_id, points, reward_type, scan_id, prod_id, deals_shared_opened_id, referrals_id):
    try:

        session_main = Session_main()
        session = Session()

        submission = models.points(
            user_id=user_id,
            points=points,
            reward_type=str(reward_type),
            scan_id=scan_id,
            prod_id=prod_id,
            deals_shared_opened_id=deals_shared_opened_id,
            referrals_id=referrals_id,
            earned_on=datetime.datetime.utcnow()
        )

        session_main.add(submission)
        session_main.commit()
        session_main.close()

        sql_query = 'update user set points = points + ' + str(points) + ' where id = ' + str(user_id)

        session_main.execute(sql_query)
        session_main.commit()
        session_main.close()

        session.execute(sql_query)
        session.commit()
        session.close()

    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('add_points', error_message)
