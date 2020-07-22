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


@app.route('/v2/info', methods=['POST'])
@multi_auth.login_required
def api_info():
    try:
        start = time.time()

        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' /v2/info:')
        try:
            submission = request.get_json()
        except Exception as e:
            print(e)
            email_crash_report('/info', e)

            result = '{"status": "MUST BE IN JSON FORMAT"}'
            return Response(result, mimetype="application/json")

        if 'info_id' in submission:
            info_id = submission['info_id']

        else:
            result = '{"status": "missing info_id: string"}'
            return Response(result, mimetype="application/json")

        if info_id == 'smart products':

            info_record = {'title': 'What is a Smart Product?','image': 'https://www.topsavings.com/appimages/smart_products.png', 'text': 'By comparing brands and sizes, the product with the lowest unit price is found at a store near you. \n Prices are checked and updated often, so Smart Products will change when prices change. \n Unit pricing is calculated by the price divided by the size or weight of the product.'}

        else:
            info_record = {}

        result = json.dumps(info_record)

        end = time.time()
        execution_time = end - start

        p_api_act = threading.Thread(target=record_api_activity, args=(g.user_id, None, None, '/v2/info', str(get_user_ip()), execution_time))
        p_api_act.start()


        print('Execution time (/v2/info): %s' % (end - start))
        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/v2/info ' + str(info_id) , error_message)
        return False


