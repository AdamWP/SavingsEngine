# -*- coding: utf-8 -*-

from __main__ import request
from __main__ import g
from __main__ import models
from __main__ import Session_main
from __main__ import Session


def calc_check_digit(value):
    """calculate check digit, they are the same for both UPCA and UPCE"""
    check_digit = 0
    odd_pos = True
    for char in str(value)[::-1]:
        if odd_pos:
            check_digit += int(char) * 3
        else:
            check_digit += int(char)
        odd_pos = not odd_pos  # alternate
    check_digit = check_digit % 10
    check_digit = 10 - check_digit
    check_digit = check_digit % 10
    return check_digit


def check_gps(gps):
    session = Session()

    if gps is None or gps == '' or gps == ',':
        # some android phones return empty gps coords or just a comma.  Using last known GPS or Glebe loblaws until it's sorted out.

        print('BAD GPS')

        gps_info = session.query(models.api_activity).filter(
            (models.api_activity.user_id == g.user_id) &
            (models.api_activity.gps_lat is not None) &
            (models.api_activity.gps_lng is not None)
        ).distinct().order_by(models.api_activity.id.desc()).first()
        session.close()

        if gps_info:
            gps_lat = gps_info.gps_lat
            gps_lng = gps_info.gps_lng

            gps = str(gps_lat) + ',' + str(gps_lng)

            if g.user_id == 0 or g.user_id == '0':
                gps = '45.410531, -75.685675'
                p_email_alert = threading.Thread(target=email_alert, args=(
                    '😖🌍 TopSavings Missing GPS ',
                    'User was defaulted to Glebe Loblaws', None), kwargs={'alert_type': 'bad_gps'})
                p_email_alert.start()
            else:
                p_email_alert = threading.Thread(target=email_alert, args=(
                    '😖🌍 TopSavings Missing GPS ',
                    'Prior GPS coords were used for user ' + str(g.user_id), None), kwargs={'alert_type': 'bad_gps'})
                p_email_alert.start()
        else:
            gps = '45.410531, -75.685675'
            p_email_alert = threading.Thread(target=email_alert, args=(
                '😖🌍 TopSavings Missing GPS ',
                'User was defaulted to Glebe Loblaws: user ' + str(g.user_id), None), kwargs={'alert_type': 'bad_gps'})
            p_email_alert.start()


    # check if user is in USA gps_lat < 41.  If so run in demo mode
    gps_coords = gps.split(",")

    gps_lat = float(gps_coords[0])
    gps_lng = float(gps_coords[1])

    # todo combine the training mode query above with this one
    # user_id = 4 is apple, user_id = 197 is Amazon, user_id = 283 is Steve's Dad
    if g.user_id == 2 or g.user_id == 4 or g.user_id == 197 or g.user_id == 283 or g.user_id == 1790 or g.user_id == 393 or (41 > gps_lat > 36 and -124 < gps_lng < -119):
        print('Demo Mode: Actual GPS: ' + str(gps) + ' user_id:' + str(g.user_id))
        gps = '45.280230, -75.711167'

    elif g.user_id == 7:
        gps = '49.222702, -123.001439'

    gps_coords = gps.split(",")
    gps_lat = float(gps_coords[0])
    gps_lng = float(gps_coords[1])
    gps_lat = round(gps_lat, 8)
    gps_lng = round(gps_lng, 8)
    gps_lat = str(gps_lat)
    gps_lng = str(gps_lng)

    return {'gps_lat': gps_lat, 'gps_lng': gps_lng}


def get_user_ip():
    if request.headers.getlist("X-Forwarded-For"):
        user_ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        user_ip = request.remote_addr

    return user_ip


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        pass

    try:
        import unicodedata
        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass

    return False


def record_api_activity(user_id, gps_lat, gps_lng, endpoint, ipaddress, execution_time, *positional_parameters, **keyword_parameters):

    session = Session_main()

    if ('user_activity' in keyword_parameters):
        user_activity = keyword_parameters['user_activity']
    else:
        user_activity = None

    if user_id is None:
        user_id = 'null'

    sql_query_a = 'insert into api_activity (user_id, date, date_time,endpoint, execution_time'
    sql_query_b = ') values(' + str(user_id) + ', date(now()), now(), "' + str(endpoint) + '", ' + str(execution_time)

    if ipaddress is not None:
        sql_query_a = sql_query_a + ', ipaddress'
        sql_query_b = sql_query_b + ', "' + str(ipaddress) + '"'

    if gps_lat is not None and gps_lng is not None:
        sql_query_a = sql_query_a + ', gps_lat, gps_lng'
        sql_query_b = sql_query_b + ', ' + str(gps_lat) + ',' + str(gps_lng)

    if 'search_id' in keyword_parameters:
        search_id = keyword_parameters['search_id']
        sql_query_a = sql_query_a + ', search_id'
        sql_query_b = sql_query_b + ', "' + str(search_id) + '"'

    if 'prod_id' in keyword_parameters:
        prod_id = keyword_parameters['prod_id']
        if prod_id is not None:
            sql_query_a = sql_query_a + ', prod_id'
            sql_query_b = sql_query_b + ', "' + str(prod_id) + '"'

    if 'scan_id' in keyword_parameters:
        scan_id = keyword_parameters['scan_id']
        if scan_id is not None and scan_id != '':
            sql_query_a = sql_query_a + ', scan_id'
            sql_query_b = sql_query_b + ', "' + str(scan_id) + '"'

    if 'deal_id' in keyword_parameters:
        deal_id = keyword_parameters['deal_id']
        if deal_id is not None:
            sql_query_a = sql_query_a + ', deal_id'
            sql_query_b = sql_query_b + ', "' + str(deal_id) + '"'

    if 'share_id' in keyword_parameters:
        share_id = keyword_parameters['share_id']
        sql_query_a = sql_query_a + ', share_id'
        sql_query_b = sql_query_b + ', "' + str(share_id) + '"'

    if 'note' in keyword_parameters:
        note = keyword_parameters['note']
        if note is not None and note != '':
            sql_query_a = sql_query_a + ', note'
            sql_query_b = sql_query_b + ', "' + str(note) + '"'

    if 'os_type' in keyword_parameters:
        os_type = keyword_parameters['os_type']
        sql_query_a = sql_query_a + ', OS'
        sql_query_b = sql_query_b + ', "' + str(os_type) + '"'

    if 'tab' in keyword_parameters:
        tab = keyword_parameters['tab']
        sql_query_a = sql_query_a + ', tab'
        sql_query_b = sql_query_b + ', "' + str(tab) + '"'

    if 'generic_name' in keyword_parameters:
        generic_name = keyword_parameters['generic_name']
        if generic_name is not None:
            sql_query_a = sql_query_a + ', generic_name'
            sql_query_b = sql_query_b + ', "' + str(generic_name) + '"'

    if 'user_activity' in keyword_parameters:
        non_user_activity = keyword_parameters['user_activity']
        if non_user_activity is not None:
            sql_query_a = sql_query_a + ', user_activity'
            sql_query_b = sql_query_b + ', 1'

    if 'page' in keyword_parameters:
        page = keyword_parameters['page']
        sql_query_a = sql_query_a + ', page'
        sql_query_b = sql_query_b + ', "' + str(page) + '"'

    sql_query = sql_query_a + sql_query_b + ')'

    session.execute(sql_query)
    session.commit()
    session.close()


