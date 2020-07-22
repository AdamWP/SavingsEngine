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
import re

import boto
import boto.s3.connection
from boto.s3.key import Key

from src.authentication import multi_auth
from src.email import email_crash_report
from src.utils import get_user_ip
from src.utils import check_gps
from src.utils import record_api_activity

from src.prices import get_prices
from src.points import get_points_token
from src.points import add_points
from src.stores import get_current_store
from src.shopping_list import add_user_savings

from settings import AWS_ACCESS_KEY_ID
from settings import AWS_SECRET_ACCESS_KEY
from settings import S3_ENDPOINT
from settings import S3_HOST
from settings import SCANS_IMAGE_BUCKET
from settings import PRODUCT_IMAGE_BUCKET_NAME
from settings import STORE_IMAGE_BUCKET

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from settings import SMTP_SERVER
from settings import SMTP_PORT
from settings import SMTP_LOGIN
from settings import SMTP_PASSWORD

@app.route('/v2/scan', methods=['POST'])
@app.route('/scan', methods=['POST'])
@multi_auth.login_required
def api_scan():
    try:
        start = time.time()

        session_main = Session_main()
        session = Session()
        output_record = {}
        scan_type = None
        points = 0
        points_message = None
        prod_id = None
        prod_id_alt = None
        product_size = None
        product_units = None
        prod_id_list = []
        points_rewards = []
        auto_submit = False
        currency = None
        quantity = None
        note = None
        image = None

        user_ipaddress = str(get_user_ip())
        print(str(datetime.datetime.now()) + ' IP:' + user_ipaddress + ' user_id:' + str(g.user_id) + ' /scan:')

        try:
            scan_submission = request.get_json()

        except Exception as e:
            print(e)
            email_crash_report('/scan', e)

            result = '{"status": "MUST BE IN JSON FORMAT"}'
            print(str(datetime.datetime.now()) + ' IP:' + user_ipaddress + ' user_id:' + str(g.user_id) + ' ' + result)
            return Response(result, mimetype="application/json")

        if 'gps' in scan_submission:
            gps = scan_submission['gps']
            gps_info = check_gps(gps)
            if gps_info:
                gps_lat = gps_info['gps_lat']
                gps_lng = gps_info['gps_lng']
                gps = str(gps_lat) + ',' + str(gps_lng)
            else:
                result = '{"status": "GPS Error"}'
                return Response(result, mimetype="application/json")
        else:
            result = '{"status": "GPS Error"}'
            return Response(result, mimetype="application/json")

        if 'scan_type' in scan_submission:
            print('SCAN TYPE')
            scan_type = scan_submission['scan_type']
            if scan_type is not None:
                scan_type = scan_type.strip()
                if 'prod_id_' in scan_type:
                    prod_id = scan_type
                    prod_id = prod_id.replace('prod_id_', '')

                else:
                    prod_id = None
            if scan_type == '':
                scan_type = None
                prod_id = None
        else:
            result = '{"status": "missing scan_type : string (price_tag, barcode, or prod_id_###)"}'
            return Response(result, mimetype="application/json")

        if 'barcode' in scan_submission:
            barcode = scan_submission['barcode']
            if barcode is not None:
                barcode = barcode.strip()
            if barcode == '':
                barcode = None
        else:
            result = '{"status": "missing barcode : string, null"}'
            return Response(result, mimetype="application/json")

        if scan_type == 'barcode' and barcode is None:
            result = '{"status": "null barcode"}'
            return Response(result, mimetype="application/json")

        if 'upc' in scan_submission:
            upc = scan_submission['upc']
            if upc is not None:
                upc = upc.strip()
            if upc == '':
                upc = None
        else:
            result = '{"status": "missing upc : string, null"}'
            return Response(result, mimetype="application/json")

        if 'sku' in scan_submission:
            sku = scan_submission['sku']
            if sku is not None:
                sku = sku.strip()

            if sku == '':
                sku = None
        else:
            result = '{"status": "missing sku : string, null"}'
            return Response(result, mimetype="application/json")

        if 'price' in scan_submission:
            price = scan_submission['price']
            if price is not None:
                price = price.strip()
            if price == '':
                price = None
        else:
            result = '{"status": "missing price: string, null"}'
            return Response(result, mimetype="application/json")

        if 'price_dollars' in scan_submission:
            price_dollars = scan_submission['price_dollars']
            if price_dollars is not None:
                price_dollars = price_dollars.strip()
            if price_dollars == '':
                price_dollars = None
        else:
            result = '{"status": "missing price_dollars: string, null"}'
            return Response(result, mimetype="application/json")

        if 'price_cents' in scan_submission:
            price_cents = scan_submission['price_cents']
            if price_cents is not None:
                price_cents = price_cents.strip()
            if price_cents == '':
                price_cents = None
        else:
            result = '{"status": "missing price_cents: string, null"}'
            return Response(result, mimetype="application/json")

        if 'unit_price' in scan_submission:
            unit_price = scan_submission['unit_price']
            if unit_price is not None:
                unit_price = unit_price.strip()
            if unit_price == '':
                unit_price = None
        else:
            result = '{"status": "missing unit_price: string, null"}'
            return Response(result, mimetype="application/json")

        if 'price_multi' in scan_submission:
            price_multi = scan_submission['price_multi']
            if price_multi is not None:
                price_multi = price_multi.strip()
            if price_multi == '':
                price_multi = None
        else:
            result = '{"status": "missing price_multi: string, null"}'
            return Response(result, mimetype="application/json")

        if 'price_over_limit' in scan_submission:
            price_over_limit = scan_submission['price_over_limit']
            if price_over_limit is not None:
                price_over_limit = price_over_limit.strip()
            if price_over_limit == '':
                price_over_limit = None
        else:
            result = '{"status": "missing price_over_limit: string, null"}'
            return Response(result, mimetype="application/json")

        if 'save_price' in scan_submission:
            save_price = scan_submission['save_price']
            if save_price is not None:
                save_price = save_price.strip()
            if save_price == '':
                save_price = None
        else:
            result = '{"status": "missing save_price: string, null"}'
            return Response(result, mimetype="application/json")

        if 'orig_price' in scan_submission:
            orig_price = scan_submission['orig_price']
            if orig_price is not None:
                orig_price = orig_price.strip()
            if orig_price == '':
                orig_price = None
        else:
            result = '{"status": "missing orig_price: string, null"}'
            return Response(result, mimetype="application/json")

        if 'limit' in scan_submission:
            limit = scan_submission['limit']
            if limit is not None:
                limit = limit.strip()
            if limit == '':
                limit = None
        else:
            result = '{"status": "missing limit: string, null"}'
            return Response(result, mimetype="application/json")

        if 'size' in scan_submission:
            product_size_scanned = scan_submission['size']
            if product_size_scanned is not None:
                product_size_scanned = product_size_scanned.strip()
            if product_size_scanned == '':
                product_size_scanned = None
        else:
            result = '{"status": "missing size: string, null"}'
            return Response(result, mimetype="application/json")

        if 'product_name' in scan_submission:
            product_name_scanned = scan_submission['product_name']
            if product_name_scanned is not None:
                product_name_scanned = product_name_scanned.strip()
            if product_name_scanned == '':
                product_name_scanned = None
        else:
            result = '{"status": "missing product_name: string, null"}'
            return Response(result, mimetype="application/json")

        if 'end_date' in scan_submission:
            end_date = scan_submission['end_date']
            if end_date is not None:
                end_date = end_date.strip()
            if end_date == '':
                end_date = None
        else:
            result = '{"status": "missing end_date: string, null"}'
            return Response(result, mimetype="application/json")

        if 'extra_text' in scan_submission:
            extra_text = scan_submission['extra_text']
            if extra_text is not None:
                extra_text = extra_text.strip()
            if extra_text == '':
                extra_text = None
        else:
            extra_text = None
            # result = '{"status": "missing extra_text: string, null"}'
            # return Response(result, mimetype="application/json")

        current_store_info = get_current_store(gps_lat, gps_lng)
        current_store_id = current_store_info['current_store_id']
        store_id = current_store_id
        store_chain = current_store_info['chain']

        print('CURRENT STORE IS ' + str(store_chain))

        # submit gps, userid, store_id and post time to database and get scan ID, then submit known items scanned to submission table and unknown items to unknown_submission table

        scan_uuid = str(uuid.uuid4())

        submission = models.scans(
            post_time=datetime.datetime.utcnow(),
            user_id=int(g.user_id),
            store_id=store_id,
            gps_lat=gps_lat,
            gps_lng=gps_lng,
            ipaddress=user_ipaddress,
            scan_type=scan_type,
            prod_id=prod_id,
            uuid=scan_uuid

        )

        session_main.add(submission)
        session_main.commit()
        scan_id = submission.scan_id
        print('NEW SCAN ' + str(scan_id))
        session_main.close()

        sql_data = ''

        if 'size' in scan_submission:
            size_scanned = scan_submission['size']
            if size_scanned is not None:
                size_scanned = size_scanned.strip()
            if size_scanned is not None and size_scanned != '':
                if sql_data != '':
                    sql_data = sql_data + ','
                sql_data = sql_data + '("size",' + str(scan_id) + ',"' + str(size_scanned) + '","' + str(scan_uuid) + '")'
        else:
            size_scanned = None

        if prod_id is not None:
            print('PROD_ID IN SUBMISSION')
            print(prod_id)
            prod_id_scanned = prod_id
            if prod_id_scanned is not None:
                prod_id_scanned = prod_id_scanned.strip()
            if prod_id_scanned is not None and prod_id_scanned != '':
                if sql_data != '':
                    sql_data = sql_data + ','
                sql_data = sql_data + '("prod_id",' + str(scan_id) + ',"' + str(prod_id_scanned) + '","' + str(scan_uuid) + '")'
        else:
            prod_id_scanned = None

        if 'product_name' in scan_submission:
            product_name_scanned = scan_submission['product_name']
            if product_name_scanned is not None:
                product_name_scanned = product_name_scanned.strip()
            if product_name_scanned is not None and product_name_scanned != '':
                if sql_data != '':
                    sql_data = sql_data + ','
                sql_data = sql_data + '("product_name",' + str(scan_id) + ',"' + str(product_name_scanned) + '","' + str(scan_uuid) + '")'
        else:
            product_name_scanned = None

        if 'end_date' in scan_submission:
            end_date = scan_submission['end_date']
            if end_date is not None:
                end_date = end_date.strip()
            if end_date is not None and end_date != '':
                if sql_data != '':
                    sql_data = sql_data + ','
                sql_data = sql_data + '("end_date",' + str(scan_id) + ',"' + str(end_date) + '","' + str(scan_uuid) + '")'
        else:
            end_date = None

        if 'extra_text' in scan_submission:
            extra_text = scan_submission['extra_text']
            if extra_text is not None:
                extra_text = extra_text.strip()
            if extra_text is not None and extra_text != '':
                if sql_data != '':
                    sql_data = sql_data + ','
                sql_data = sql_data + '("extra_text",' + str(scan_id) + ',"' + str(extra_text) + '","' + str(scan_uuid) + '")'
        else:
            extra_text = None

        if 'price' in scan_submission:
            price = scan_submission['price']
            scanned_price = price
            if price is not None and price != '':

                currency = '$'
                quantity = 1
                # clean up price
                price = price.replace(',', '.')
                price = price.replace('s', '')
                price = price.replace('S', '')
                price = price.replace('A', '4')

                # remove all non numeric and period
                non_decimal = re.compile(r'[^\d.]+')
                price = non_decimal.sub('', price)

                try:
                    price = float(price)
                    price = str(price)

                except ValueError:
                    print('Price is not decimal')
                    price = None
                    quantity = None

                if sql_data != '':
                    sql_data = sql_data + ','

                sql_data = sql_data + '("price",' + str(scan_id) + ',"' + str(scanned_price) + '","' + str(scan_uuid) + '")'
        else:
            price = None

        if 'price_dollars' in scan_submission:
            price_dollars = scan_submission['price_dollars']
            if price_dollars is not None:
                price_dollars = price_dollars.strip()
            if price_dollars is not None and price_dollars != '':
                if sql_data != '':
                    sql_data = sql_data + ','
                sql_data = sql_data + '("price_dollars",' + str(scan_id) + ',"' + str(price_dollars) + '","' + str(scan_uuid) + '")'
        else:
            price_dollars = None

        if 'price_cents' in scan_submission:
            price_cents = scan_submission['price_cents']
            if price_cents is not None:
                price_cents = price_cents.strip()
            if price_cents is not None and price_cents != '':
                if sql_data != '':
                    sql_data = sql_data + ','
                sql_data = sql_data + '("price_cents",' + str(scan_id) + ',"' + str(price_cents) + '","' + str(scan_uuid) + '")'
        else:
            price_cents = None

        if 'price_multi' in scan_submission:
            price_multi = scan_submission['price_multi']
            if price_multi is not None:
                price_multi = price_multi.strip()
            if price_multi is not None and price_multi != '':
                if sql_data != '':
                    sql_data = sql_data + ','
                sql_data = sql_data + '("price_multi",' + str(scan_id) + ',"' + str(price_multi) + '","' + str(scan_uuid) + '")'
        else:
            price_multi = None

        if 'unit_price' in scan_submission:
            unit_price = scan_submission['unit_price']
            if unit_price is not None:
                unit_price = unit_price.strip()
            if unit_price is not None and unit_price != '':
                if sql_data != '':
                    sql_data = sql_data + ','
                sql_data = sql_data + '("unit_price",' + str(scan_id) + ',"' + str(unit_price) + '","' + str(scan_uuid) + '")'
        else:
            unit_price = None

        if 'price_over_limit' in scan_submission:
            price_over_limit = scan_submission['price_over_limit']
            if price_over_limit is not None:
                price_over_limit = price_over_limit.strip()
            if price_over_limit is not None and price_over_limit != '':
                if sql_data != '':
                    sql_data = sql_data + ','
                sql_data = sql_data + '("price_over_limit",' + str(scan_id) + ',"' + str(price_over_limit) + '","' + str(scan_uuid) + '")'
        else:
            price_over_limit = None

        if 'save_price' in scan_submission:
            save_price = scan_submission['save_price']
            if save_price is not None:
                save_price = save_price.strip()
            if save_price is not None and save_price != '':
                if sql_data != '':
                    sql_data = sql_data + ','
                sql_data = sql_data + '("save_price",' + str(scan_id) + ',"' + str(save_price) + '","' + str(scan_uuid) + '")'
        else:
            save_price = None

        if 'orig_price' in scan_submission:
            orig_price = scan_submission['orig_price']
            if orig_price is not None:
                orig_price = orig_price.strip()
            if orig_price is not None and orig_price != '':
                if sql_data != '':
                    sql_data = sql_data + ','
                sql_data = sql_data + '("orig_price",' + str(scan_id) + ',"' + str(orig_price) + '","' + str(scan_uuid) + '")'
        else:
            orig_price = None

        if 'limit' in scan_submission:
            limit = scan_submission['limit']
            if limit is not None:
                limit = limit.strip()
            if limit is not None and limit != '':
                if sql_data != '':
                    sql_data = sql_data + ','
                sql_data = sql_data + '("limit",' + str(scan_id) + ',"' + str(limit) + '","' + str(scan_uuid) + '")'
        else:
            limit = None

        if 'barcode' in scan_submission:
            barcode = scan_submission['barcode']

            if barcode is not None:
                barcode = barcode.strip()
            if barcode is not None and barcode != '':
                if sql_data != '':
                    sql_data = sql_data + ','
                sql_data = sql_data + '("barcode",' + str(scan_id) + ',"' + str(barcode) + '","' + str(scan_uuid) + '")'
            if barcode == '' or barcode is None:
                barcode = None
            else:
                #sanitize barcode.  Some scans were producing strange characters
                barcode = str(barcode)
                barcode = barcode.split("\\", 1)[0]
                barcode = barcode.strip('\u001d')
        else:
            barcode = None

        if 'upc' in scan_submission:
            upc = scan_submission['upc']

            if upc is not None:
                upc = upc.strip()
            if upc is not None and upc != '':
                upc = upc.strip()
                # prepare UPC data submission to db
                if sql_data != '':
                    sql_data = sql_data + ','
                sql_data = sql_data + '("upc",' + str(scan_id) + ',"' + str(upc) + '","' + str(scan_uuid) + '")'
                print('Sanitize UPC')
                upc = upc.replace('-', '')
                upc = upc.replace(' ', '')

            if upc == '' or upc is None or upc.isnumeric() == False:
                upc = None
        else:

            upc = None

        if 'sku' in scan_submission:
            sku = scan_submission['sku']

            if sku is not None:
                sku = sku.strip()

            if sku is not None and sku != '':
                if sql_data != '':
                    sql_data = sql_data + ','
                sql_data = sql_data + '("sku",' + str(scan_id) + ',"' + str(sku) + '","' + str(scan_uuid) + '")'
            if sku == '':
                sku = None
        else:
            sku = None

        if sql_data != '':
            sql_data = 'INSERT INTO scans_data (data_type, scan_id, data, uuid) VALUES ' + sql_data

            p_save_scan_data = threading.Thread(target=save_scan_data, args=(str(sql_data),))
            p_save_scan_data.start()

        if prod_id is not None and prod_id != '':

            print('Product identified on device ' + str(prod_id))

            item_sql = 'select * from item_info where prod_id = "' + prod_id + '"'

            item_info = session.execute(item_sql)
            session.close()
            item_info = list(item_info)

            if item_info:

                # Get product details
                for row in item_info:
                    
                    if row.prod_name is not None and row.prod_name != '':
                        prod_name = row.prod_name
                    else:
                        prod_name = None

                    if row.image is not None and row.image != '':
                        image = row.image

                    else:
                        image = None

                    if row.size is not None and row.size != '':
                        product_size = row.size
                    else:
                        product_size = None

                    if row.units is not None and row.units != '':
                        product_units = row.units

                    else:
                        product_units = None

                    if row.units is not None and row.units != '':
                        awaiting_approval = row.awaiting_approval

                    else:
                        awaiting_approval = None
            else:
                prod_id = None
                note = 'unknown prod_id submitted'

        elif scan_type == 'barcode' and barcode is not None:

            #todo may want to give priority to code type 'UPC' rather than all codes
            item_sql = 'select product_codes.*, item_info.* from product_codes, item_info where product_codes.prod_id = item_info.prod_id and product_codes.code = "' + barcode + '" order by product_codes.id, item_info.id desc limit 1'

            item_info = session.execute(item_sql)
            session.close()
            item_info = list(item_info)

            if item_info:
                # Get product details

                for row in item_info:
                    prod_id = row.prod_id
                    
                    if row.prod_name is None:
                        prod_name = None
                    else:
                        prod_name = row.prod_name

                    if row.image is None:
                        image = None
                    else:
                        image = row.image

                    if row.size is None:
                        product_size = None
                    else:
                        product_size = row.size

                    if row.units is None:
                        product_units = None
                    else:
                        product_units = row.units

                    if row.units is not None and row.units != '':
                        awaiting_approval = row.awaiting_approval

                    else:
                        awaiting_approval = None

            else:
                auto_submit = False
                prod_id = None
                prod_name = None
                product_size = None
                product_units = None

        elif scan_type == 'price_tag' and (barcode is not None or upc is not None or sku is not None):

            item_sql = 'select product_codes.*, item_info.* from product_codes, item_info where product_codes.prod_id = item_info.prod_id and ('

            prod_code_count = 0

            if store_chain == 'Food Basics' and barcode is not None:
                # Food basics barcodes are Food basics SKU
                if prod_code_count > 0:
                    item_sql = item_sql + ' or '

                #todo may want to add chain='Food Basics' and others.  Possible same as Metro, if so merge
                item_sql = item_sql + 'product_codes.type = "sku" and product_codes.code = "' + barcode + '"'
                prod_code_count = prod_code_count + 1

            elif (store_chain == 'Loblaws' or store_chain == 'Independent' or store_chain == 'No Frills' or store_chain == 'Superstore' or store_chain == 'Rexall' or store_chain == 'Shoppers') and barcode is not None:
                # Loblaws & affiliated, and rexall stores barcodes are UPC-A
                if prod_code_count > 0:
                    item_sql = item_sql + ' or '

                item_sql = item_sql + 'product_codes.type = "upc-a" and product_codes.code = "' + barcode + '"'
                prod_code_count = prod_code_count + 1

            elif store_chain == 'Metro' and barcode is not None:
                # Metro barcodes Metro SKU
                if prod_code_count > 0:
                    item_sql = item_sql + ' or '

                # todo may want to add chain='Metro' and maybe more?  Possible same as Food basics.  if so merge
                item_sql = item_sql + 'product_codes.type = "sku" and product_codes.code = "' + barcode + '"'
                prod_code_count = prod_code_count + 1

            elif store_chain == 'Walmart' and barcode is not None:
                # walmart_numbers are same as walmart barcode stripped of the leading 3 digits and last digit
                barcode_walmart = barcode[3:-1]
                if prod_code_count > 0:
                    item_sql = item_sql + ' or '
                item_sql = item_sql + 'product_codes.type = "item_number" and chain = "Walmart" and product_codes.code = "' + barcode_walmart + '"'
                prod_code_count = prod_code_count + 1

            #elif store_chain == 'Sobeys' or store_chain == 'Giant Tiger' or store_chain == 'Whole Foods or store_chain = 'Amazon'

            elif barcode is not None:
                if prod_code_count > 0:
                    item_sql = item_sql + ' or '
                item_sql = item_sql + 'product_codes.code = "' + barcode + '"'
                prod_code_count = prod_code_count + 1

            if upc is not None:

                upc_a = upc
                # build full UPC-A
                # remove spaces and dashes
                upc = upc.replace('-', '')
                upc = upc.replace(' ', '')
                # remove leading zeros
                if len(upc_a) > 12:
                    upc_a = upc_a.lstrip("0")

                #add leading zeros to build upc_a without check
                if len(upc_a) < 11:
                    upc_a_len = len(upc_a)
                    missing_digits_len = 11 - upc_a_len
                    for i in range(missing_digits_len):
                        upc_a = '0' + str(upc_a)

                # add check digit
                if len(upc_a) == 11:
                    odd_sum = 0
                    even_sum = 0
                    for i, char in enumerate(upc_a):
                        j = i + 1
                        if j % 2 == 0:
                            even_sum += int(char)
                        else:
                            odd_sum += int(char)

                    total_sum = (odd_sum * 3) + even_sum
                    mod = total_sum % 10
                    check_digit = 10 - mod
                    if check_digit == 10:
                        check_digit = 0
                    upc_a = str(upc_a) + str(check_digit)

                if prod_code_count > 0:
                    item_sql = item_sql + ' or '
                item_sql = item_sql + 'product_codes.type = "upc-a" and product_codes.code = "' + upc_a + '"'
                prod_code_count = prod_code_count + 1

            if store_chain == 'Food Basics' and sku is not None:
                # Food basics sku are unique to them, maybe metro is the same?
                if prod_code_count > 0:
                    item_sql = item_sql + ' or '

                # todo may want to add chain='Food Basics' and maybe more?  Possible same as Metro.  if so merge
                item_sql = item_sql + 'product_codes.type = "sku" and product_codes.code = "' + sku + '"'
                prod_code_count = prod_code_count + 1

            #ML model is identifying incorrect SKU's on new digital shelf end price tags at loblaws. Needs fixing
            #elif (store_chain == 'Loblaws' or store_chain == 'Independent' or store_chain == 'No Frills' or store_chain == 'Superstore') and sku is not None:

            #    sku_ea = str(sku) + '_EA'
                # Loblaws & affiliated skus are internal.  May have _EA appended

            #    if prod_code_count > 0:
            #        item_sql = item_sql + ' or '

            #    item_sql = item_sql + 'product_codes.type = "sku" and (product_codes.chain = "Loblaws" or product_codes.chain = "realcanadiansuperstore" or product_codes.chain = "nofrills" or product_codes.chain = "yourindependentgrocer") and (product_codes.code = "' + sku + '" or product_codes.code = "' + sku_ea + '")'
            #    prod_code_count = prod_code_count + 1

            elif store_chain == 'Metro' and sku is not None:
                # Metro Sku's are unique.  May be same as food basics.  Look into it
                if prod_code_count > 0:
                    item_sql = item_sql + ' or '

                # todo may want to add chain='Metro' and maybe more?  Possible same as Food basics.  if so merge
                item_sql = item_sql + 'product_codes.type = "sku" and product_codes.code = "' + sku + '"'
                prod_code_count = prod_code_count + 1

            elif store_chain == 'Rexall' and sku is not None:
                # Rexall sku's are questionable.  Needs further investigation to make sur they're unique.  5 digit number on standard price tags.  Missing from sales tags.
                if prod_code_count > 0:
                    item_sql = item_sql + ' or '

                # todo may want to add chain='Metro' and maybe more?  Possible same as Food basics.  if so merge
                item_sql = item_sql + 'product_codes.type = "sku" and chain = "Rexall" and product_codes.code = "' + sku + '"'
                prod_code_count = prod_code_count + 1

            elif store_chain == 'Sobeys' and sku is not None:
                # Sobey's sku's are 6 digit and possibly first 6 digits from barcode.
                if prod_code_count > 0:
                    item_sql = item_sql + ' or '

                item_sql = item_sql + 'product_codes.type = "sku" and chain = "Sobeys" and product_codes.code = "' + sku + '"'
                prod_code_count = prod_code_count + 1

            elif store_chain == 'Walmart' and sku is not None:
                # Sku is walmart item #.  Same as barcode minus first 3 and last digits
                if prod_code_count > 0:
                    item_sql = item_sql + ' or '

                item_sql = item_sql + 'product_codes.type = "item_number" and chain = "Walmart" and product_codes.code = "' + sku + '"'
                prod_code_count = prod_code_count + 1

            elif sku is not None:
                if prod_code_count > 0:
                    item_sql = item_sql + 'or '
                item_sql = item_sql + 'product_codes.code = "' + sku + '"'
                prod_code_count = prod_code_count + 1

            item_sql = item_sql + ') order by product_codes.id, item_info.id desc limit 1'

            item_info = session.execute(item_sql)
            session.close()
            item_info = list(item_info)

            if item_info:
                print('TYPE PRICE_TAG IS IN DB')
                # Get product details
                for row in item_info:
                    prod_id = row.prod_id
                    # If there's more than one code, CHECK TO MAKE SURE ALL CODES ARE ONBOARDED FOR PRODUCT  STORE
                    #todo beef this up

                    if (sku is not None and upc is not None) or (sku is not None and barcode is not None) or (upc is not None and barcode is not None):
                        p_check_codes = threading.Thread(target=check_codes, args=(prod_id, sku, upc, barcode, store_chain, gps_lat, gps_lng, g.user_id))
                        p_check_codes.start()

                    if row.prod_name is None:
                        prod_name = None
                    else:
                        prod_name = row.prod_name

                    if row.image is None:
                        image = None
                    else:
                        image = row.image

                    if row.size is None:
                        product_size = None
                    else:
                        product_size = row.size

                    if row.units is None:
                        product_units = None
                    else:
                        product_units = row.units

                    if row.units is not None and row.units != '':
                        awaiting_approval = row.awaiting_approval

                    else:
                        awaiting_approval = None

            elif product_name_scanned is not None and product_name_scanned != '':
                print('TYPE PRICE_TAG IS NOT IN DB')
                print('SUBMIT WITH OCR DATA')
                # SUBMIT WITH OCR'd data
                prod_id = str(uuid.uuid4())
                prod_name = product_name_scanned
                product_size = product_size_scanned
                image = None
                submission = models.item_info(
                    auto_submitted_on=datetime.datetime.utcnow(),
                    auto_submitted_by=int(g.user_id),
                    prod_id=prod_id,
                    prod_name=product_name_scanned,
                    size=product_size_scanned,
                    submitted_scan_id=scan_id,
                    ipaddress=user_ipaddress,
                    awaiting_approval=1
                )
                session_main.add(submission)
                session_main.commit()
                session_main.close()

                submission = models.item_info(
                    prod_id=prod_id,
                    prod_name=product_name_scanned,
                    size=product_size_scanned,
                    awaiting_approval=1
                )
                session.add(submission)
                session.commit()
                session.close()

                p_check_codes = threading.Thread(target=check_codes, args=(prod_id, sku, upc, barcode, store_chain, gps_lat, gps_lng, g.user_id))
                p_check_codes.start()

                add_points(g.user_id, 10, 'new_product_found', scan_id, prod_id, None, None)
                auto_submit = True
                points = points + 10
                points_message = 'New Product Found!'

            else:

                auto_submit = False
                prod_id = None
                prod_name = None
                product_size = None
                product_units = None

        elif scan_type == 'price_tag' and (barcode is None and upc is None and sku is None):
            # todo try identifying by text
            # cannot find product try again or take pic
            note = 'note enough info(barcode or upc or sku) from price tag'

        if prod_id is not None:

            session_main.query(models.scans).filter(
                (models.scans.scan_id == scan_id)).update(
                {'prod_id': prod_id})
            session_main.commit()
            session_main.close()

            prod_id_list.append(prod_id)
            output_record = {}
            output_record['type'] = 'Product'
            output_record['prod_id'] = str(prod_id)

            output_record['prod_name'] = prod_name
            if image == '' or image is None:
                image = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/no_image_grocery_lg.png'
                image_thumb = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/no_image_grocery_sm.png'

            elif auto_submit is True or awaiting_approval is not None:
                image_thumb = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME + '/sm_new/' + str(image)
                image = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME + '/sm_new/' + str(image)

            else:
                image_thumb = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME + '/sm_new/' + str(image)
                image = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME + '/sm_new/' + str(image)

            output_record['image'] = image
            output_record['image_thumb'] = image_thumb

            # todo update nutrition
            output_record['nutr_score'] = None

            output_record['nutr_info'] = None

            if product_size is not None and product_size != '':
                product_size = str(product_size)
                if product_units is not None and product_units != '':
                    product_size = product_size + ' ' + product_units
            else:
                product_size = None
                if product_units is not None and product_units != '':
                    product_size = product_units

            output_record['size'] = product_size

            # see if user has item in their shopping list and send appropriate icon

            list_info = session.query(models.shopping_list).filter(
             (models.shopping_list.prod_id == prod_id) &
             (models.shopping_list.user_id == g.user_id)
            ).distinct().first()
            session.close()
            if list_info:
                output_record['is_in_shopping_list'] = True
                output_record['points_rewards'] = points_rewards
            else:
                output_record['is_in_shopping_list'] = False

                points_info = get_points_token('add_to_list', scan_id, prod_id)

                points_reward_info = {}
                points_reward = points_info['points_reward']
                points_token = points_info['points_token']

                points_reward_info['type'] = 'add_to_list'
                points_reward_info['points_token'] = points_token
                points_reward_info['points_reward'] = points_reward

                points_rewards.append(points_reward_info)

                output_record['points_rewards'] = points_rewards

            if price is not None and price != '':
                print('Submitted Scan to database A')

                points = points + 5
                add_points(g.user_id, 5, 'price_scanned', scan_id, prod_id, None, None)

                if points_message != 'New Product Found!':
                    points_message = 'Price Scanned!'
                else:
                    points_message = 'New Product + Price Scanned!'

            all_prices = get_prices(prod_id, gps_lat, gps_lng, current_store_id)
            prices = all_prices['prices']

            output_record['prices'] = prices

        else:

            note = 'cannot find product try again or take pic'

            scan_error = True
            output_record = {}
            output_record['type'] = None
            output_record['error'] = 404.1
            output_record['error_message'] = None
            output_record['prod_name'] = ''
            output_record['image'] = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/try_again_lg.png'

            output_record['is_in_shopping_list'] = False

            points_info = get_points_token('take_product_picture', scan_id, None)

            points_reward_info = {}
            points_reward = points_info['points_reward']
            points_token = points_info['points_token']

            points_reward_info['type'] = 'take_product_picture'
            points_reward_info['points_token'] = points_token
            points_reward_info['points_reward'] = points_reward

            points_rewards.append(points_reward_info)

            output_record['points_rewards'] = points_rewards
            output_record['prices'] = []

        #p_add_savings = threading.Thread(target=add_user_savings, args=(g.user_id, g.distance, 'scan', gps_lat, gps_lng, prod_id, scan_id))
        #p_add_savings.start()

        if prod_id is None or auto_submit is True:
            output_record['upload'] = True
        else:
            output_record['upload'] = True

        output_record['scan_id'] = str(scan_id)

        if points > 0 and points is not None:
            output_record['points'] = points
        else:
            output_record['points'] = None

        if points_message != '' and points_message is not None:
            output_record['points_message'] = points_message
        else:
            output_record['points_message'] = None

        # output.append(output_record)
        result = json.dumps(output_record)

        # todo handle wordy prices
        if price is not None:
            price_temp = price.replace('.', '')

            if len(price_temp) > 5:
                price = None
                currency = None
                quantity = None

            if price_temp.isnumeric() is False:
                price = None
                currency = None
                quantity = None

        end = time.time()
        execution_time = end - start

        p_api_act = threading.Thread(target=record_api_activity, args=(g.user_id, gps_lat, gps_lng, '/scan', str(get_user_ip()), execution_time), kwargs={'scan_id': scan_id, 'user_activity': 1, 'prod_id': prod_id})
        p_api_act.start()

        save_scan(scan_id, scan_uuid, store_id, prod_id, gps_lat, gps_lng, quantity, price, currency, note, execution_time)

        p_report_scan = threading.Thread(target=report_scan, args=(scan_id, gps_lat, gps_lng, execution_time))
        p_report_scan.start()

        print('Scan Execution time (/scan): %s' % (end - start))

        return Response(result, mimetype="application/json")

    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/scan', error_message)
        return False


def report_scan(scan_id, gps_lat, gps_lng, execution_time):

    try:
        session_main = Session_main()
        execution_time = round(execution_time, 2)

        # wait 5 minutes for image upload to complete
        time.sleep(300)

        str_sql = 'select uuid, image, price, (select prod_name from item_info where prod_id = scans.prod_id order by id limit 1) as prod_name from scans where scan_id = "' + str(scan_id) + '"'

        item_info = session_main.execute(str_sql)
        session_main.close()

        for row in item_info:

            if row.uuid is not None and row.uuid != '':
                scan_uuid = row.uuid
            else:
                scan_uuid = None

            if row.image is not None and row.image != '':
                image = row.image

            else:
                image = None

            if row.price is not None and row.price != '':
                price = row.price
                price = '{0:.2f}'.format(price)
                price = '$' + str(price)
            else:
                price = None

            if row.prod_name is not None and row.prod_name != '':
                prod_name = row.prod_name

            else:
                prod_name = 'Unknown Product'

        print('REPORT PRICE CHECK')

        msg = MIMEMultipart('alternative')
        if price is not None:
            msg['Subject'] = '✅ 🤳🏷️ New Price Check (Price Tag)'
            html_gps = '<html><body>Is the price correct?<BR><a href="https://cms.topsavings.com/email_set_price_accuracy?u=' + str(scan_uuid) + '&a=accurate&s=' + str(scan_id) + '">Price is ' + str(price) + ' 👍</a> - <a href="https://cms.topsavings.com/email_set_price_accuracy?u=' + str(scan_uuid) + '&a=inaccurate&s=' + str(scan_id) + '">NOT ' + str(price) + ' 👎</a><BR>' + str(prod_name) + ' (' + str(execution_time) + ' seconds)<BR><img src="http://tsscanskzenmmb6azpa43bx.s3-api.us-geo.objectstorage.softlayer.net/scans/' + str(image) + '" width="600"><BR>Location:  https://www.google.com/maps/place/' + str(gps_lat) + ',' + str(gps_lng) + '<BR> Click https://cms.topsavings.com/cms_scans to review in CMS</body></html>'

            html_no_gps = '<html><body>Is the price correct?<BR><a href="https://cms.topsavings.com/email_set_price_accuracy?u=' + str(scan_uuid) + '&a=accurate&s=' + str(scan_id) + '">Price is ' + str(price) + ' 👍</a> - <a href="https://cms.topsavings.com/email_set_price_accuracy?u=' + str(scan_uuid) + '&a=inaccurate&s=' + str(scan_id) + '">NOT ' + str(price) + ' 👎</a><BR>' + str(prod_name) + ' (' + str(execution_time) + ' seconds)<BR><img src="http://tsscanskzenmmb6azpa43bx.s3-api.us-geo.objectstorage.softlayer.net/scans/' + str(image) + '" width="600"><BR> Click https://cms.topsavings.com/cms_scans to review in CMS</body></html>'

        else:
            msg['Subject'] = '✅ 🤳🥫 New Price Check (Product)'
            html_gps = '<html><body>' + str(prod_name) + ' (' + str(execution_time) + ' seconds)<BR><img src="http://tsscanskzenmmb6azpa43bx.s3-api.us-geo.objectstorage.softlayer.net/scans/' + str(image) + '" width="600"><BR>Location:  https://www.google.com/maps/place/' + str(gps_lat) + ',' + str(gps_lng) + ' <BR> Click https://cms.topsavings.com/cms_scans to review in CMS</body></html>'


            html_no_gps = '<html><body>' + str(prod_name) + ' (' + str(execution_time) + ' seconds)<BR><img src="http://tsscanskzenmmb6azpa43bx.s3-api.us-geo.objectstorage.softlayer.net/scans/' + str(image) + '" width="600"><BR> Click https://cms.topsavings.com/cms_scans to review in CMS</body></html>'

        msg['From'] = 'TopSavings API <mailer@TopSavings.com>'
        msg['To'] = 'TopSavings Team'

        part2 = MIMEText(html_gps, 'html')

        msg.attach(part2)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.ehlo()
        server.starttls()
        server.login(SMTP_LOGIN, SMTP_PASSWORD)

        server.sendmail("mailer@TopSavings.com", "adam@topsavings.com", msg.as_string())
        server.sendmail("mailer@TopSavings.com", "steve@topsavings.com", msg.as_string())
        server.quit()

        return False

    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' ' + str(fname) + ' ' + str(exc_tb.tb_lineno)
        email_crash_report('report_scan', error_message)
        return False


def check_codes(prod_id, sku, upc, barcode, store_chain, gps_lat, gps_lng, user_id):

    session = Session()
    session_main = Session_main()

    if store_chain is None:
        print('EMAIL UNKNOWN STORE')

        msg = MIMEMultipart('alternative')
        msg['Subject'] = '🏬 TopSavings Unknown Store'
        msg['From'] = 'TopSavings API <mailer@TopSavings.com>'
        msg['To'] = 'TopSavings Team'

        text = 'TopSavings user ' + str(user_id) + ' scanned a pricetag in an unknown store at https://www.google.com/maps/place/' + str(gps_lat) + ',' + str(gps_lng)

        part1 = MIMEText(text, 'plain')

        msg.attach(part1)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.ehlo()
        server.starttls()
        server.login(SMTP_LOGIN, SMTP_PASSWORD)

        server.sendmail("mailer@TopSavings.com", "adam@topsavings.com", msg.as_string())

        server.quit()

    if sku is not None:
        if store_chain == 'Walmart':
            code_type = 'item_number'
        else:
            code_type = 'sku'

        str_sql = "insert into product_codes(prod_id, code, type, chain, added_by, added_datetime) select * from (select '" + str(prod_id) + "','" + str(sku) + "','" + str(code_type) + "','" + str(store_chain) + "','" + str(user_id) + "',now()) as tmp where not exists (select * from product_codes where prod_id = '" + str(prod_id) + "' and code = '" + str(sku) + "' and type = '" + code_type + "' and chain = '" + str(store_chain) + "') limit 1"

        session_main.execute(str_sql)
        session_main.commit()
        session_main.close()

        str_sql = "insert into product_codes(prod_id, code, type, chain) select * from (select '" + str(prod_id) + "','" + str(sku) + "','" + str(code_type) + "','" + str(store_chain) + "') as tmp where not exists (select * from product_codes where prod_id = '" + str(prod_id) + "' and code = '" + str(sku) + "' and type = '" + code_type + "' and chain = '" + str(store_chain) + "') limit 1"

        session.execute(str_sql)
        session.commit()
        session.close()

    if upc is not None:

        # convert UPC to full UPC-A with check digit
        if len(upc) > 12:
            upc = upc.lstrip("0")

        if len(upc) < 11:
            upc_len = len(upc)
            missing_digits_len = 11 - upc_len
            for i in range(missing_digits_len):
                upc = '0' + str(upc)

        if len(upc) == 11:
            odd_sum = 0
            even_sum = 0
            for i, char in enumerate(upc):
                j = i + 1
                if j % 2 == 0:
                    even_sum += int(char)
                else:
                    odd_sum += int(char)

            total_sum = (odd_sum * 3) + even_sum
            mod = total_sum % 10
            check_digit = 10 - mod
            if check_digit == 10:
                check_digit = 0
            upc = str(upc) + str(check_digit)

        str_sql = "insert into product_codes(prod_id, code, type, added_by, added_datetime) select * from (select '" + str(prod_id) + "','" + str(upc) + "','upc-a','" + str(user_id) + "',now()) as tmp where not exists (select * from product_codes where prod_id = '" + str( prod_id) + "' and code = '" + str(upc) + "' and type = 'upc-a') limit 1"

        session_main.execute(str_sql)
        session_main.commit()
        session_main.close()

        str_sql = "insert into product_codes(prod_id, code, type) select * from (select '" + str(prod_id) + "','" + str(upc) + "','upc-a') as tmp where not exists (select * from product_codes where prod_id = '" + str(prod_id) + "' and code = '" + str(upc) + "' and type = 'upc-a') limit 1"

        session.execute(str_sql)
        session.commit()
        session.close()

    if barcode is not None:

        if store_chain == 'Loblaws' or store_chain == 'Independent' or store_chain == 'No Frills' or store_chain == 'Superstore' or store_chain == 'Shoppers' or store_chain == 'Rexall':
            code_type = 'upc-a'
        elif store_chain == 'Metro' or store_chain == 'Sobeys' or store_chain == 'Food Basics':
            code_type = 'sku'
        elif store_chain == 'Walmart':
            code_type = 'item_number'
        else:
            code_type = 'barcode'

        str_sql = "insert into product_codes(prod_id, code, type, chain, added_by, added_datetime) select * from (select '" + str(prod_id) + "','" + str(barcode) + "','" + str(code_type) + "','" + str(store_chain) + "','" + str(user_id) + "',now()) as tmp where not exists (select * from product_codes where prod_id = '" + str(prod_id) + "' and code = '" + str(barcode) + "' and type = '" + code_type + "' and chain = '" + str(store_chain) + "') limit 1"

        session_main.execute(str_sql)
        session_main.commit()
        session_main.close()

        str_sql = "insert into product_codes(prod_id, code, type, chain) select * from (select '" + str(prod_id) + "','" + str(barcode) + "','" + str(code_type) + "','" + str(store_chain) + "') as tmp where not exists (select * from product_codes where prod_id = '" + str(prod_id) + "' and code = '" + str(barcode) + "' and type = '" + code_type + "' and chain = '" + str(store_chain) + "') limit 1"

        session.execute(str_sql)
        session.commit()
        session.close()

    return None


def convert_upc(upc):

    print('CONVERT UPC TO UPC-A')

    # convert UPC to full UPC-A with check digit
    if len(upc) > 12:
        upc = upc.lstrip("0")

    if len(upc) < 11:
        upc_len = len(upc)
        missing_digits_len = 11 - upc_len
        for i in range(missing_digits_len):
            upc = '0' + str(upc)

    if len(upc) == 11:
        odd_sum = 0
        even_sum = 0
        for i, char in enumerate(upc):
            j = i + 1
            if j % 2 == 0:
                even_sum += int(char)
            else:
                odd_sum += int(char)

        total_sum = (odd_sum * 3) + even_sum
        mod = total_sum % 10
        check_digit = 10 - mod
        if check_digit == 10:
            check_digit = 0
        upc = str(upc) + str(check_digit)

    print(upc)
    return upc


def save_scan_data(scan_data_query):
    print('Submitting scanned data to database')
    start = time.time()
    session_main = Session_main()
    session_main.execute(scan_data_query)
    session_main.commit()
    session_main.close()

    end = time.time()
    execution_time = end - start

    print('SAVE SCAN DATA EXECUTION TIME ' + str(execution_time))
    return None


def save_scan(scan_id, scan_uuid, store_id, prod_id, gps_lat, gps_lng, quantity, price, currency, note, scan_time):

    start = time.time()
    print('Submitting scanned price to database')

    session_main = Session_main()

    expiry = datetime.datetime.utcnow() + datetime.timedelta(days=1)

    # update scans table
    if prod_id is not None and prod_id != '':

        sql_query = 'update scans set expired = 1, expiry = "' + str(expiry) + '", prod_id = "' + str(prod_id) + '"'

    else:
        sql_query = 'update scans set expired = 1, expiry = "' + str(expiry) + '", prod_id = null'

    if quantity is not None:
        sql_query = sql_query + ', quantity = "' + str(quantity) + '"'

    if price is not None:
        sql_query = sql_query + ', price = "' + str(price) + '"'

    if currency is not None:
        sql_query = sql_query + ', currency = "' + str(currency) + '"'

    if note is not None:
        sql_query = sql_query + ', note = "' + str(note) + '"'

    if scan_time is not None:
        sql_query = sql_query + ', scan_time = ' + str(scan_time)

    sql_query = sql_query + ' where scan_id = "' + str(scan_id) + '"'

    session_main.execute(sql_query)
    session_main.commit()
    session_main.close()

    #todo save unit_price

    submission = models.scans(
        post_time=datetime.datetime.utcnow(),
        scan_type='price_check',
        expiry=expiry,
        store_id=store_id,
        price=price,
        currency=currency,
        quantity=quantity,
        prod_id=prod_id,
        uuid= scan_uuid,
        expired=1
    )

    #session.add(submission)
    #session.commit()
    #session.close()

    end = time.time()
    execution_time = end - start

    print('SAVE SCAN EXECUTION TIME ' + str(execution_time))
    return None


@app.route('/v2/upload', methods=['GET', 'POST'])
@app.route('/upload', methods=['GET', 'POST'])
@multi_auth.login_required
def upload():
    try:

        # For some reason many scans have unreadable data.
        print('DEBUG UPLOAD')
        print('request')
        print(request)
        print('request.method')
        print(request.method)
        print('request.headers')
        print(request.headers)
        #print('request.data')
        #print(request.data)
        print('request.mimetype')
        print(request.mimetype)
        #print('request.get_json()')
        #print(request.get_json())
        print('request.files')
        print(request.files)
        print('request.form')
        print(request.form)

        start = time.time()
        session_main = Session_main()
        barcode = None
        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' /upload:')
        if request.method == 'POST':
            print()
            # check if the post has the file part
            if 'file' not in request.files:
                print('no file part')
                return ('no file part')
            else:
                print('file in request')
                file = request.files['file']
                if 'scan_id' in request.form:
                    scan_id = request.form['scan_id']
                else:
                    result = '{"status": "missing scan_id: string"}'
                    return Response(result, mimetype="application/json")

                if 'upload_type' in request.form:
                    upload_type = request.form['upload_type']
                else:
                    result = '{"status": "missing upload_type: string (scan or product_picture)"}'
                    return Response(result, mimetype="application/json")


                    # todo upload should have "Type" to differentiate between new scan and front of product picture.  Type wasn't being sent to API so we're checking the db to see if scan image was sent or not.  If so, then upload is a product image, if not then scan image.
                    # scan_image_info = session.query(models.scans).filter(
                    #    (models.scans.scan_id == scan_id) &
                    #    (models.scans.image is not None)
                    # ).distinct().first()
                    # session.close()

                    # if scan_image_info:
                    #    upload_type = 'product_picture'

                extension = os.path.splitext(file.filename)[1]
                # change file name to new unique file name
                f_name = str(uuid.uuid4()) + extension

                print('Saving Image : ' + str(f_name))

                ##conn for AWS
                ##conn = boto.connect_s3(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)

                ##conn for IBM Softlayer
                conn = boto.connect_s3(aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, host=S3_HOST, calling_format=boto.s3.connection.OrdinaryCallingFormat(), )

                if upload_type == 'product_picture':

                    bucket = conn.get_bucket(PRODUCT_PICS_BUCKET, validate=False)
                    UPLOADED_FILENAME = 'product_pictures/' + f_name

                    add_product_picture = models.item_info_unknown_images(
                        scan_id=str(scan_id),
                        image=str(f_name),
                        ipaddress=str(get_user_ip()),
                        submitted_on=datetime.datetime.utcnow(),
                        submitted_by=int(g.user_id)
                    )
                    session_main.add(add_product_picture)
                    session_main.commit()
                    session_main.close()

                else:

                    bucket = conn.get_bucket(SCANS_IMAGE_BUCKET, validate=False)
                    UPLOADED_FILENAME = 'scans/' + f_name

                    session_main.query(models.scans).filter(
                        (models.scans.scan_id == scan_id)).update({'image': f_name})
                    session_main.commit()
                    session_main.close()

                # include folders in file path. If it doesn't exist, it will be created
                k = Key(bucket)
                k.key = UPLOADED_FILENAME

                k.set_contents_from_file(file)
                k.set_acl('public-read')
                print('/upload j')
                if extension == '.jpg':
                    k.copy(k.bucket, k.name, preserve_acl=True, metadata={'Content-Type': 'image/jpeg'})
                elif extension == '.gif':
                    k.copy(k.bucket, k.name, preserve_acl=True, metadata={'Content-Type': 'image/gif'})
                elif extension == '.png':
                    k.copy(k.bucket, k.name, preserve_acl=True, metadata={'Content-Type': 'image/png'})

                if upload_type == 'product_picture':
                    p = threading.Thread(target=get_suggestion_for_unknown, args=(scan_id, f_name))
                    p.start()

                end = time.time()

                execution_time = end - start
                p_api_act = threading.Thread(target=record_api_activity, args=(
                    g.user_id, None, None, '/upload', str(get_user_ip()), execution_time), kwargs={'scan_id': scan_id})
                # todo add gps
                p_api_act.start()

                print('Execution time (upload success): %s' % (end - start))
                return json.dumps({'filename': f_name})
        else:

            end = time.time()

            print('Execution time (upload failed): %s' % (end - start))
            return Response('{"Wrong Method"}', mimetype="application/json")
    # else:
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/upload', error_message)
        return False
