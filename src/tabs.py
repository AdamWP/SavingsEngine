# -*- coding: utf-8 -*-
from __main__ import app
from __main__ import Session
from __main__ import g
from __main__ import Response
from __main__ import request
from __main__ import json
from __main__ import requests


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


@app.route('/v2/tap_tab', methods=['POST'])
@multi_auth.login_required
def api_tap_tab():

    try:
        start = time.time()

        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' /tap_tab:')
        try:
            submission = request.get_json()
        except:
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

        if 'tab_name' in submission:
            tab = submission['tab_name']
            if tab is not None:
                tab = tab.strip()
            if tab == '':
                result = '{"status": "tab_name cannot be null or blank : string"}'
                return Response(result, mimetype="application/json")
        else:
            result = '{"status": "missing tab_name: string"}'
            return Response(result, mimetype="application/json")

        end = time.time()

        execution_time = end - start

        p_api_act = threading.Thread(target=record_api_activity,args=(g.user_id, gps_lat, gps_lng, '/tap_tab', str(get_user_ip()), execution_time), kwargs={'tab': tab, 'user_activity': 1})
        p_api_act.start()

        result = '{"status": "OK"}'
        print('Execution time (/tap_tab): %s' % (end - start))
        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/tap_tab', error_message)
        return False


