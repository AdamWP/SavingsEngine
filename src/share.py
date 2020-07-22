# -*- coding: utf-8 -*-
from __main__ import app
from __main__ import Session
from __main__ import Session_main
from __main__ import g
from __main__ import Response
from __main__ import request
from __main__ import json
from __main__ import models
from __main__ import requests

import sys
import os
import time
import datetime
import threading

import string
import random
from decimal import Decimal

from io import BytesIO
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw

import boto
import boto.s3.connection
from boto.s3.key import Key

from settings import AWS_ACCESS_KEY_ID
from settings import AWS_SECRET_ACCESS_KEY


from src.authentication import multi_auth
from src.email import email_crash_report
from src.email import email_alert
from src.utils import get_user_ip
from src.utils import check_gps
from src.utils import record_api_activity

from src.stores import get_current_store
from src.prices import get_prices
from src.prices import get_best_price

from settings import S3_ENDPOINT
from settings import S3_HOST
from settings import PRODUCT_IMAGE_BUCKET_NAME
from settings import STORE_IMAGE_BUCKET
from settings import DEALS_IMAGE_BUCKET


@app.route('/v2/get_share', methods=['POST'])
@app.route('/get_share', methods=['POST'])
@multi_auth.login_required
def api_get_share():
    try:
        start = time.time()
        session_main = Session_main()

        print(
            str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' /get_share:')
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

        if 'prod_id' in submission:
            prod_id = submission['prod_id']
        else:
            result = '{"status": "missing prod_id : string"}'
            return Response(result, mimetype="application/json")

        # if the store is amazon then the price isn't getting passed back from the app.  It's currently sending 'price': 'Amazon', 'saving_price': 'View on'.  Get the correct price.

        best_price_info = get_best_price(g.user_id, g.distance, gps_lat, gps_lng, prod_id, None, None, None)

        price = best_price_info['best_price']
        if price is not None  and price != '':
            price = Decimal(price)

        saving_price = best_price_info['saving_price']
        if saving_price is not None and price != '':
            saving_price = Decimal(saving_price)

        currency = '$'
        store_id = best_price_info['best_store_id']

        BASE_LIST = string.digits + string.ascii_letters
        share_id = ''.join((random.choice(BASE_LIST)) for char in range(7))

        if store_id != '' and store_id is not None:

            # try 10 times to find a random string that's not in the db already
            i = 0
            while i < 10:

                str_sql = 'select deal_id from deals_shared where deal_id = "' + str(share_id) + '"'
                item_info = session_main.execute(str_sql)
                session_main.close()

                old_deal_id = None
                # todo do a better job of checking if there are results
                for row in item_info:
                    old_deal_id = row.deal_id

                if old_deal_id is None:
                    i = 10
                else:
                    i = i + 1

            p_make_images = threading.Thread(target=make_share_image, args=(share_id, prod_id, price, saving_price, currency, store_id, g.user_id))
            p_make_images.start()

            str_sql = 'insert into deals_shared(deal_id, user_id, date_time, prod_id, gps_lat, gps_lng'
            str_sql_b = ') values("' + str(share_id) + '","' + str(g.user_id) + '",now(),"' + str(prod_id) + '","' + str(
                gps_lat) + '","' + str(gps_lng) + '"'

            if price is not None and price != '':
                str_sql = str_sql + ', price'
                str_sql_b = str_sql_b + ',"' + str(price) + '"'

            if saving_price is not None and saving_price != '':
                str_sql = str_sql + ', saving_price'
                str_sql_b = str_sql_b + ',"' + str(saving_price) + '"'

            if store_id is not None and store_id != '':
                str_sql = str_sql + ', store_id'
                str_sql_b = str_sql_b + ',"' + str(store_id) + '"'

            if currency is not None and currency != '':
                str_sql = str_sql + ', currency'
                str_sql_b = str_sql_b + ',"' + str(currency) + '"'

            str_sql = str_sql + str_sql_b + ')'

            session_main.execute(str_sql)
            session_main.commit()
            session_main.close()

            share_url = 'https://www.topsavings.com/deals/' + str(share_id)

            result = {'share_url': share_url}
            result = json.dumps(result)
        else:
            print('Share: No Price Available. Sharing main website.')
            share_url = 'https://www.topsavings.com'
            result = {'share_url': share_url}
            result = json.dumps(result)

        end = time.time()

        if g.admin is False:
            text_alert = 'A TopSavings deal was shared.  \r\n  \r\n  '

            if store_id is not None and store_id != '':
                text_alert = text_alert + ' Shared Deal: https://s3-api.us-geo.objectstorage.softlayer.net/deals.topsavings.com/previews/' + str(share_id) + '.png     \r\n  \r\n  '

            else:
                text_alert = text_alert + ' No price available so main website was shared. \r\n  \r\n  '

            text_alert = text_alert + ' Location:  https://www.google.com/maps/place/' + str(gps_lat) + ',' + str(gps_lng)

            p_email_alert = threading.Thread(target=email_alert, args=(':OS:📲 New Deal Shared', text_alert, None), kwargs={'alert_type': 'deal_shared', 'user_id': str(g.user_id)})
            p_email_alert.start()

        execution_time = end - start
        p_api_act = threading.Thread(target=record_api_activity, args=(g.user_id, gps_lat, gps_lng, '/get_share', str(get_user_ip()), execution_time), kwargs={'user_activity': 1, 'prod_id': prod_id})
        p_api_act.start()

        print('Execution time (/get_share): %s' % (end - start))
        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/get_share', error_message)
        return False


def make_share_image(share_id, prod_id, price, saving_price, currency, store_id, user_id):
    start = time.time()
    session = Session()

    full_price = None

    item_sql = 'select logo, address, (select image from item_info where prod_id = "' + str(prod_id) + '" limit 1) as image from stores where id = "' + str(store_id) + '" limit 1'

    item_info = session.execute(item_sql)
    session.close()

    product_image_url = None
    for row in item_info:
        if row.image is None:

            product_image_url = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/no_image_grocery_lg.png'
        else:
            product_image_url = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME + '/lg_new/' + str(row.image)

        if row.logo is None:
            logo = None
        else:
            logo = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/stores/' + str(row.logo)

        if row.address is None:
            address = None
        elif row.address == 'Delivery':
            address = None
        else:
            address = str(row.address)

    # THIS IS THE PRODUCT IMAGE FOR WEBSITE

    sharing_image = Image.open("images/wideshare.png")

    bottom_bar = Image.open("images/bottom_bar.png")
    sharing_image.paste(bottom_bar, (0, 540), bottom_bar)

    product_image = requests.get(product_image_url)
    file_object = product_image.content
    fp = BytesIO(file_object)
    product_image = Image.open(fp)

    # temp_filename = 'temp1prod.png'
    # product_image.save(temp_filename)

    web_image = Image.open(fp)

    prod_max_height = 480
    prod_max_width = 480
    web_max_height = 540
    web_max_width = 530

    if product_image.size[1] > product_image.size[0]:
        wpercent = (prod_max_height / float(product_image.size[1]))
        wsize = int((float(product_image.size[0]) * float(wpercent)))
        product_image = product_image.resize((wsize, prod_max_height), Image.ANTIALIAS)

    else:
        hpercent = (prod_max_width / float(product_image.size[0]))
        hsize = int((float(product_image.size[1]) * float(hpercent)))
        product_image = product_image.resize((prod_max_width, hsize), Image.ANTIALIAS)

    product_image_width = product_image.size[0]
    product_image_height = product_image.size[1]

    # we want at least a 30 right side margin
    prod_image_h_space = 480 - product_image_width

    prod_image_h_space = prod_image_h_space / 2
    prod_image_h_space = 690 + prod_image_h_space
    prod_image_h_space = int(prod_image_h_space)

    prod_image_v_space = 540 - product_image_height
    prod_image_v_space = prod_image_v_space / 2
    prod_image_v_space = int(prod_image_v_space)

    sharing_image.paste(product_image, (prod_image_h_space, prod_image_v_space))

    if web_image.size[1] > web_image.size[0]:
        wpercent = (web_max_height / float(web_image.size[1]))
        wsize = int((float(web_image.size[0]) * float(wpercent)))
        web_image = web_image.resize((wsize, web_max_height), Image.ANTIALIAS)

    else:
        hpercent = (web_max_width / float(web_image.size[0]))
        hsize = int((float(web_image.size[1]) * float(hpercent)))
        web_image = web_image.resize((web_max_width, hsize), Image.ANTIALIAS)

    web_image_width = web_image.size[0]
    web_image_height = web_image.size[1]

    if price is not None and saving_price is not None:
        full_price = price + saving_price

        saving_percent = saving_price / full_price

        saving_percent = saving_percent * 100
        saving_percent = int(saving_percent)

        crest_text = str(saving_percent) + '%'

        crest_image = Image.open("images/crest.png")

        font = ImageFont.truetype("fonts/Textaxis-Eina03-Bold.ttf", 60)
        # crest_text_image = Image.new('RGBA', (140, 105), (255, 255, 255, 0))
        t1 = ImageDraw.Draw(crest_image)

        w, h = t1.textsize(crest_text, font=font)

        # t1.text((0, -25), crest_text, (255, 255, 255), font=font)

        t1.text((int((210 - w) / 2), 40), crest_text, (255, 255, 255), font=font)

        # temp_filename = 'temp1x.png'
        # crest_image.save(temp_filename)

        font = ImageFont.truetype("fonts/Textaxis-Eina03-Bold.ttf", 40)

        t1.text((62, 105), 'OFF', (255, 255, 255), font=font)

        crest_image = crest_image.rotate(11, resample=Image.BICUBIC, expand=True)

        # crest_image.paste(crest_text_image, (48, 45), crest_text_image)

        # temp_filename = 'temp1.png'
        # crest_image.save(temp_filename)

        web_image.paste(crest_image, (0, 0), crest_image)
    elif price is not None:
        full_price = price

    else:
        full_price = ''

    # pad web version. This is done after the crest is applied so crest is in correct position

    web_image_padded = Image.new('RGBA', (web_max_width, web_max_height), (255, 255, 255, 1))

    padding_width = (web_max_width - web_image.size[0]) / 2
    padding_width = int(padding_width)
    padding_height = (web_max_height - web_image.size[1]) / 2
    padding_height = int(padding_height)

    web_image_padded.paste(web_image, (padding_width, padding_height))

    # we want at least a 30 right side margin
    prod_image_h_space = 480 - product_image_width

    prod_image_h_space = prod_image_h_space / 2
    prod_image_h_space = 690 + prod_image_h_space
    prod_image_h_space = int(prod_image_h_space)

    prod_image_v_space = 540 - product_image_height
    prod_image_v_space = prod_image_v_space / 2
    prod_image_v_space = int(prod_image_v_space)

    sharing_image.paste(product_image, (prod_image_h_space, prod_image_v_space))

    if saving_price is not None and saving_price != '':
        sharing_image.paste(crest_image, (650, 30), crest_image)

        # temp_filename = 'temp1fff.png'
        # sharing_image.save(temp_filename)

        saving_price_disp = 'SAVE $' + str(saving_price)
        font = ImageFont.truetype("fonts/Textaxis-Eina03-Bold.otf", 22)
        w, h = t1.textsize(saving_price_disp, font=font)

        t1 = ImageDraw.Draw(sharing_image)

        t1.text((int((728 - w) / 2), 208), saving_price_disp, (255, 255, 255), font=font)


    if price is not None and price != '':
        price_disp = '$' + str(price)
        font = ImageFont.truetype("fonts/Textaxis-Eina03-Bold.otf", 108)
        t1 = ImageDraw.Draw(sharing_image)
        w, h = t1.textsize(price_disp, font=font)

        t1.text((320, 340), price_disp, (0, 0, 0), font=font)

    if full_price is not None and full_price != '' and full_price != price:
        full_price = '$' + str(full_price)
        font = ImageFont.truetype("fonts/Textaxis-Eina03-Bold.otf", 80)
        t1 = ImageDraw.Draw(sharing_image)
        w, h = t1.textsize(full_price, font=font)

        t1.text((330, 255), full_price, (128, 128, 128), font=font)

        x_image = Image.open("images/x.png")
        sharing_image.paste(x_image, (323, 280), x_image)

        was_image = Image.open("images/was.png")
        sharing_image.paste(was_image, (183, 296), was_image)

        # temp_filename = 'temp4.png'
        # sharing_image.save(temp_filename)

    # add date and disclaimer

    font = ImageFont.truetype("fonts/Textaxis-Eina03-SemiBold.otf", 16)
    t1 = ImageDraw.Draw(sharing_image)

    date_sourced = '*Price crowd sourced by TopSavings member on ' + str(
        datetime.datetime.now().date()) + '. Price not gauranteed & may change at any time without notice.'
    w, h = t1.textsize(date_sourced, font=font)

    t1.text((int((1200 - w) / 2), 510), date_sourced, (186, 186, 186), font=font)

    BASE_LIST = string.digits + string.ascii_letters

    # conn for AWS
    # conn = boto.connect_s3(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)

    # conn for IBM Softlayer
    conn = boto.connect_s3(aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                           host=S3_HOST, calling_format=boto.s3.connection.OrdinaryCallingFormat(), )

    bucket = conn.get_bucket(DEALS_IMAGE_BUCKET, validate=False)
    UPLOADED_FILENAME = '/products/' + share_id + '.png'

    k = Key(bucket)
    k.key = UPLOADED_FILENAME

    # NOTE, we're saving the image into a BytesIO object to avoid writing to disk
    out_image = BytesIO()
    # You MUST specify the file type because there is no file name to discern it from
    web_image_padded.save(out_image, 'png')
    k.set_contents_from_string(out_image.getvalue(), headers={"Content-Type": "image/png"})
    k.set_acl('public-read')

    UPLOADED_FILENAME = '/previews/' + share_id + '.png'

    k = Key(bucket)
    k.key = UPLOADED_FILENAME

    out_image = BytesIO()
    sharing_image.save(out_image, 'png')
    k.set_contents_from_string(out_image.getvalue(), headers={"Content-Type": "image/png"})
    k.set_acl('public-read')

    end = time.time()

    execution_time = end - start

    p_api_act = threading.Thread(target=record_api_activity, args=(user_id, None, None, 'make_share_image', None, execution_time))
    p_api_act.start()

    print('Execution time (make_share_image): %s' % (end - start))
    return False


@app.route('/v2/share_info', methods=['POST'])
@app.route('/share_info', methods=['POST'])
@multi_auth.login_required
def api_share_info():
    try:
        start = time.time()
        session_main = Session_main()

        ipaddress = get_user_ip()
        print(
            str(datetime.datetime.now()) + ' IP:' + str(ipaddress) + ' user_id:' + str(g.user_id) + ' /share_info:')
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

        if 'share_id' in submission:
            share_id = submission['share_id']
            is_admin = False
            if 'deal_' in share_id:
                is_admin = True

            share_id = share_id.replace('deal_', '')

        else:
            result = '{"status": "missing share_id : string"}'
            return Response(result, mimetype="application/json")

        str_sql = 'select prod_id from deals_shared where deal_id = "' + str(share_id) + '"'

        item_info = session_main.execute(str_sql)
        session_main.close()

        prod_id = None

        for row in item_info:
            prod_id = row.prod_id
            if prod_id is not None:
                prod_id = prod_id.strip()
                if prod_id == '':
                    prod_id = None
                else:
                    if is_admin is False:
                        print('IS NOT ADMIN')
                        p_share_opened = threading.Thread(target=record_share_opened, args=(share_id, ipaddress, g.user_id, gps_lat, gps_lng))
                        p_share_opened.start()
                    else:
                        print('IS ADMIN')

        result = {'prod_id': prod_id}
        result = json.dumps(result)

        end = time.time()

        execution_time = end - start
        p_api_act = threading.Thread(target=record_api_activity, args=(
        g.user_id, gps_lat, gps_lng, '/share_info', str(get_user_ip()), execution_time))
        p_api_act.start()
        print(result)
        print('Execution time (/share_info): %s' % (end - start))
        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/share_info', error_message)
        return False


def record_share_opened(share_id, ipaddress, user_id, gps_lat, gps_lng):
    session_main = Session_main()

    print('Shared Opened')
    sql_query = 'insert into deals_shared_opened (date_time, ipaddress, share_id, user_id) values(now(), "' + str(ipaddress) + '","' + share_id + '","' + str(user_id) + '")'

    session_main.execute(sql_query)
    session_main.commit()
    session_main.close()

    if user_id != 1 and user_id != 3 and user_id != 5:
        text_alert = 'A TopSavings share was opened by user ' + user_id + '.  \r\n  \r\n  Location:  https://www.google.com/maps/place/' + str(
            gps_lat) + ',' + str(gps_lng) + ' \r\n  \r\n  https://www.topsavings.com/deals/deal_' + str(share_id)
        p_email_alert = threading.Thread(target=email_alert, args=('📲 Share Opened', text_alert, None), kwargs={'alert_type': 'share_opened'})
        p_email_alert.start()
