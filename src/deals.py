# -*- coding: utf-8 -*-
from __main__ import app
from __main__ import Session
from __main__ import Session_deals
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
import uuid
from decimal import Decimal

import random

from src.authentication import multi_auth
from src.email import email_crash_report
from src.utils import get_user_ip
from src.utils import check_gps
from src.utils import is_number
from src.utils import record_api_activity
from src.prices import get_prices

from settings import SAVINGS_MIN
from settings import SAVINGS_MIN_PERCENT
from settings import SAVINGS_MAX_PERCENT
from settings import S3_ENDPOINT
from settings import STORE_IMAGE_BUCKET
from settings import PRODUCT_IMAGE_BUCKET_NAME

from multiprocessing.dummy import Pool


@app.route('/v2/deals', methods=['POST'])
@multi_auth.login_required
def api_deals2():

    try:
        start = time.time()
        session_deals = Session_deals()

        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' /v2/deals:')
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

        if 'page' in submission:
            page = submission['page']
            if not is_number(page):
                page = 0
        else:
            result = '{"status": "missing page: integer starting at 0"}'
            return Response(result, mimetype="application/json")

        if 'store' in submission:
            chain = submission['store']
            if chain is not None:
                chain = chain.lower()
        else:
            chain = None

        if 'category' in submission:
            category = submission['category']
        else:
            category = None

        page_size = 20
        start_record = int(page) * page_size
        new_deal_count = 0

        sql_query = 'select *, (select id from working.shopping_list where d3.prod_id = prod_id and expired is null and user_id = "' + str(g.user_id) + '" limit 1) as quantity_sl '

        if category is None:
            sql_query = sql_query + ', @num := if(@category = category, @num + 1, 1) as row_number, @category := category as dummy'

        if (category is None or category == 'For You') and chain is None:

            sql_query = sql_query + ' from (select * from (select distinct id, date_time, prod_id, IFNULL(submission_id,id) as submission_id_unq, prod_name, brand, category, size, size_units, size_quantity, quantity_units, chain, store_id, price, savings_price, savings_percent, image, awaiting_approval, logo, quantity, units, (select category from categories where id = user_deals.category limit 1) as category_text from user_deals where exists (select scan_id from working.scans where prod_id = user_deals.prod_id and expiry > now() ) and category is not null and user_id = ' + str(g.user_id) + ' group by submission_id_unq) t0  left join (select category as category_id, count(*) as category_size from user_deals where user_id = ' + str(g.user_id) + ' and category is not null and exists (select scan_id from working.scans where prod_id = user_deals.prod_id and expiry > now()) group by category) cat1 on cat1.category_id = t0.category union select * from (select distinct id, date_time, prod_id, IFNULL(submission_id,id) as submission_id_unq, prod_name, brand, category, size, size_units, size_quantity, quantity_units, chain, store_id, price, savings_price, savings_percent, image, awaiting_approval, logo, quantity, units, (select category from categories where id = d1.category limit 1) as category_text from zone_deals as d1 where exists (select scan_id from working.scans where prod_id = d1.prod_id and expiry > now() and store_id = d1.store_id) and not exists (select * from user_deals where user_id = "' + str(g.user_id) + '" and prod_id = d1.prod_id) and NOT EXISTS (SELECT * FROM working.user_categories_disabled, working.search_tags WHERE lcase(working.user_categories_disabled.category) = lcase(working.search_tags.tag) and working.search_tags.prod_id = d1.prod_id and working.user_categories_disabled.user_id =' + str(g.user_id) + ') and category is not null and zone_id = ' + str(g.zone_id)

        else:
            sql_query = sql_query + ' from (select * from (select distinct id, date_time, prod_id, IFNULL(submission_id,id) as submission_id_unq, prod_name, brand, category, size, size_units, size_quantity, quantity_units, chain, store_id, price, savings_price, savings_percent, image, awaiting_approval, logo, quantity, units, (select category from categories where id = d1.category limit 1) as category_text from zone_deals as d1 where exists (select scan_id from working.scans where prod_id = d1.prod_id and expiry > now() and store_id = d1.store_id) and NOT EXISTS (SELECT * FROM working.user_categories_disabled, working.search_tags WHERE lcase(working.user_categories_disabled.category) = lcase(working.search_tags.tag) and working.search_tags.prod_id = d1.prod_id and working.user_categories_disabled.user_id =' + str(g.user_id) + ') and category is not null and zone_id = ' + str(g.zone_id)

        if chain is not None:
            sql_query = sql_query + ' and lower(chain) = "' + chain + '"'

        if category is not None:
            sql_query = sql_query + ' and category = (select id from deals.categories where category = "' + str(category) + '" limit 1)'

        if category is None:
            sql_query = sql_query + ' group by submission_id_unq'

        sql_query = sql_query + ' order by category, savings_percent desc, savings_price desc, price) t1'

        sql_query = sql_query + ' left join (select category as category_id, count(*) as category_size from zone_deals where zone_id = ' + str(g.zone_id) + ' and category is not null and exists (select scan_id from working.scans where prod_id = zone_deals.prod_id and expiry > now())'

        if chain is not None:
            sql_query = sql_query + ' and lower(chain) = "' + chain + '"'

        sql_query = sql_query + ' group by category) cat2 on cat2.category_id = t1.category )d3 '

        if category is None:

            sql_query = sql_query + 'group by prod_id having row_number < 8'
            sql_set = "set @num := 0, @category := '';"
            session_deals.execute(sql_set)

        sql_query = sql_query + ' order by category, savings_percent desc, savings_price desc, price'

        if category is None:
            sql_query = sql_query + ', row_number'

        sql_query = sql_query + ' limit ' + str(start_record) + ', ' + str(page_size)

        item_info = session_deals.execute(sql_query)
        session_deals.close()
        item_info = list(item_info)

        output = {}
        deals_list = []

        pool = Pool(40)
        new_deals_labeled = 0

        for row in item_info:

            deal_record = {}
            if row.prod_id is not None and row.chain is not None:

                deal_id = str(uuid.uuid4())
                deal_record['deal_id'] = deal_id

                post_time = row.date_time

                deal_record['date_time'] = str(post_time)
                deal_time = datetime.datetime.now()

                deal_record['deal_time'] = str(deal_time)

                disp_time = None

                deal_record['display_time'] = disp_time

                prod_id = row.prod_id
                deal_record['prod_id'] = str(prod_id)
                prod_name = str(row.prod_name)

                category = row.category_text

                category_size = row.category_size

                brand = row.brand

                if brand is not None and brand != '':

                    if brand.lower() not in prod_name.lower():
                        prod_name = brand + ' ' + prod_name

                prod_size = row.size

                prod_units = row.size_units
                prod_size_quantity = row.size_quantity
                prod_quantity_units = row.quantity_units

                if prod_units is not None and prod_size is not None:
                    if len(prod_units) > 2:
                        prod_size = str(prod_size) + ' ' + str(prod_units)
                    else:
                        prod_size = str(prod_size) + str(prod_units)

                    if prod_size_quantity is not None and prod_size_quantity != '' and prod_quantity_units is None:
                        prod_size = str(prod_size_quantity) + ' x ' + str(prod_size)

                deal_name = prod_name

                if prod_size is None:
                    prod_size = ''

                if len(deal_name) > 50:
                    deal_name = deal_name[:50]
                elif (len(deal_name) + len(prod_size)) < 52:
                    deal_name = deal_name + ' ' + prod_size

                deal_record['category'] = category
                deal_record['category_size'] = category_size
                deal_record['deal_title'] = deal_name
                deal_record['prod_name'] = prod_name
                deal_record['size'] = prod_size
                deal_record['store_name'] = str(row.chain)
                deal_record['store_id'] = str(row.store_id)
                deal_record['store_image'] = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/stores_sm/' + str(row['logo'])

                deal_record['store_logo'] = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/stores/' + str(row['logo'])
                deal_record['store_thumb'] = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/stores_sm/' + str(row['logo'])

                all_prices = get_prices(prod_id, gps_lat, gps_lng, None)

                store_count = len(all_prices['prices'])
                if store_count > 0:
                    store_count = int(store_count) - 1
                else:
                    store_count = 0

                deal_record['store_count'] = store_count

                price = all_prices['price']

                quantity = row.quantity
                units = row.units

                if quantity is None or quantity == '':
                    quantity = 1

                if quantity > 1:
                    deal_record['pre_price'] = str(quantity) + '/'
                else:
                    deal_record['pre_price'] = None

                if units is not None and units != '':
                    deal_record['post_price'] = '/' + str(units)
                else:
                    deal_record['post_price'] = None

                if price is not None:
                    saving_price = all_prices['saving_price']
                    price = Decimal(price)
                    price = '{0:.2f}'.format(price)
                    price = Decimal(price)

                    deal_record['price'] = price

                    saving_price = Decimal(saving_price)
                    saving_price = '{0:.2f}'.format(saving_price)
                    saving_price = Decimal(saving_price)
                else:
                    saving_price = 0

                if row.savings_percent is not None:
                    save_ratio = row.savings_percent
                    save_ratio = save_ratio * 100
                    save_ratio = int(save_ratio)
                else:
                    save_ratio = 1

                deal_record['saving_price'] = saving_price

                quantity_sl = row.quantity_sl

                if quantity_sl:
                    deal_record['is_in_shopping_list'] = True
                else:
                    deal_record['is_in_shopping_list'] = False

                if post_time > deal_time:
                    deal_record['extra_text'] = 'STARTS TOMORROW'
                    deal_record['extra_color'] = '#8C00FF'
                elif ('Loblaws' in row.chain or 'Maxi' in row.chain or 'Independent' in row.chain or 'uperstore' in row.chain or 'rills' in row.chain or 'rovigo' in row.chain) and (save_ratio %2) == 0:
                    deal_record['extra_text'] = 'CURBSIDE PICKUP'
                    deal_record['extra_color'] = '#0076FF'

                elif 'Walmart' in row.chain and (save_ratio %2) == 0:
                    deal_record['extra_text'] = 'DELIVERY AVAILABLE'
                    deal_record['extra_color'] = '#0076FF'

                elif ('itacost' in row.chain or 'ell.ca' in row.chain) and (save_ratio %2) == 0:
                    deal_record['extra_text'] = 'DELIVERY AVAILABLE'
                    deal_record['extra_color'] = '#0076FF'

                elif save_ratio > 49:
                    deal_record['extra_text'] = 'GREAT DEAL - SAVE $' + str(saving_price)
                    deal_record['extra_color'] = '#fa0000'

                elif saving_price > 0:
                    deal_record['extra_text'] = 'SAVE $' + str(saving_price)
                    deal_record['extra_color'] = '#fa7000'
                else:
                    deal_record['extra_text'] = None
                    deal_record['extra_color'] = None

                new_deals_labeled = new_deals_labeled + 1

                if 49 < save_ratio < 75:
                    deal_record['crest_color'] = '#fa0000'
                    deal_record['crest_text'] = str(save_ratio) + '% OFF'

                elif 34 < save_ratio < 75:
                    deal_record['crest_color'] = '#fa7000'
                    deal_record['crest_text'] = str(save_ratio) + '% OFF'

                else:
                    deal_record['crest_color'] = None
                    deal_record['crest_text'] = None

                if row.image is None:
                    deal_record['image'] = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/no_image_grocery_lg.png'
                    deal_record['image_thumb'] = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/no_image_grocery_sm.png'
                else:
                    if row.awaiting_approval is None:
                        deal_record[
                            'image'] = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME + '/sm_new/' + str(row.image)
                        deal_record['image_thumb'] = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME + '/sm_new/' + str(row.image)

                    else:
                        deal_record['image'] = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME + '/sm_new/' + str(row.image)
                        deal_record['image_thumb'] = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME + '/sm_new/' + str(row.image)

                prices = all_prices['prices']

                deal_record['prices'] = prices

                deals_list.append(deal_record)

                pool.apply_async(record_deal_display, args=(gps_lat, gps_lng, deal_id, prod_id, row.price, row.savings_price, str(g.user_id), row.store_id, None))

        pool.close()
        pool.join()

        output['list'] = deals_list
        output['new_deal_count'] = new_deal_count
        result = json.dumps(output)

        session_deals.close()

        end = time.time()

        execution_time = end - start
        p_api_act = threading.Thread(target=record_api_activity,args=(g.user_id, gps_lat, gps_lng, '/v2/deals', str(get_user_ip()), execution_time), kwargs={'page': page})
        p_api_act.start()

        print('Execution time (/v2/deals): %s' % (end - start))

        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/v2/deals', error_message)
        return False


def record_deal_display(gps_lat, gps_lng, deal_id, prod_id, min_price, save_price, user_id, store_id, chain_count):

    session = Session_main()

    submission = models.deals_displayed(
        deal_id=deal_id,
        prod_id=prod_id,
        min_price=min_price,
        save_price=save_price,
        user_id=user_id,
        store_id=store_id,
        chain_count=chain_count,
        date_time=datetime.datetime.now(),
        gps_lat=gps_lat,
        gps_lng=gps_lng
    )
    session.add(submission)
    session.commit()
    session.close()

    return False


@app.route('/v2/tap_deal', methods=['POST'])
@app.route('/tap_deal', methods=['POST'])
@multi_auth.login_required
def api_tap_deal():

    try:
        start = time.time()
        session = Session()

        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' /tap_deal:')
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
            if prod_id is not None:
                prod_id = prod_id.strip()
            if prod_id == '':
                result = '{"status": "prod_id cannot be null or blank : string"}'
                return Response(result, mimetype="application/json")
        else:
            result = '{"status": "missing prod_id: string"}'
            return Response(result, mimetype="application/json")

        if 'deal_id' in submission:
            deal_id = submission['deal_id']
            if deal_id is not None:
                deal_id = deal_id.strip()
            if deal_id == '':
                deal_id = None
        else:
            result = '{"status": "missing deal_id: string"}'
            return Response(result, mimetype="application/json")

        if 'search_query' in submission:
            search_query = submission['search_query']
            #if search_query is not None:
            #    search_query = search_query.strip()
            #    search_query = str(search_query)
            #if search_query == '':
            #    search_query = None
        else:
            result = '{"status": "missing search_query : string/null"}'
            return Response(result, mimetype="application/json")

        if 'category' in submission:
            category = submission['category']
            if category is not None:
                category = category.strip()
                category = str(category)
            if category == '':
                category = None
        else:
            category = None
            # result = '{"status": "missing category : string/null"}'
            # return Response(result, mimetype="application/json")

        if 'scan_id' in submission:
            scan_id = submission['scan_id']
            if scan_id is not None:
                scan_id = scan_id.strip()
            if scan_id == '':
                scan_id = None
        else:
            result = '{"status": "missing scan_id : string/null"}'
            return Response(result, mimetype="application/json")

        if 'referrer' in submission:
            referrer = submission['referrer']
            if referrer is not None:
                referrer = referrer.strip()
            if referrer == '':
                result = '{"status": "referrer must not be blank or null : string, allowed values are (deals, shopping_list, search, scan, recent_scan, similar_items)"}'
                return Response(result, mimetype="application/json")
        else:
            result = '{"status": "missing referrer : string, allowed values are (deals, shopping_list, search, scan, recent_scan, similar_items)"}'
            return Response(result, mimetype="application/json")

        if 'price' in submission:
            price = submission['price']
            if price is not None:

                currency = '$'

            if price == '' or price is None:
                price = None
                currency = None
        else:
            price = None
            currency = None

        if 'saving_price' in submission:
            saving_price = submission['saving_price']
            if saving_price == '' or saving_price is None:
                saving_price = None
        else:
            saving_price = None

        if 'store_id' in submission:
            store_id = submission['store_id']
            if price is not None:
                store_id = store_id.strip()
            if store_id == '':
                store_id = None
        else:
            result = '{"status": "missing store_id : string/null"}'
            return Response(result, mimetype="application/json")

        end = time.time()

        execution_time = end - start

        p_api_act = threading.Thread(target=record_api_activity,args=(g.user_id, gps_lat, gps_lng, '/tap_deal', str(get_user_ip()), execution_time),kwargs={'prod_id': prod_id, 'scan_id': scan_id, 'deal_id': deal_id, 'user_activity': 1})
        p_api_act.start()

        p = threading.Thread(target=record_deal_tap, args=(gps_lat, gps_lng, prod_id, deal_id, search_query, scan_id, referrer, price, currency, saving_price, store_id, g.user_id, execution_time))
        p.start()

        result = '{"status": "OK"}'
        print('Execution time (/tap_deal): %s' % (end - start))
        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/tap_deal', error_message)
        return False


def record_deal_tap(gps_lat, gps_lng, prod_id, deal_id, search_query, scan_id, referrer, price, currency, saving_price, store_id, user_id, execution_time):
    session_main = Session_main()

    if price == 'Amazon':
        price = None

    submission = models.deals_tapped(
        user_id=user_id,
        deal_id=deal_id,
        prod_id=prod_id,
        search_query=search_query,
        scan_id=scan_id,
        referrer=referrer,
        price=price,
        currency=currency,
        saving_price=saving_price,
        date_time=datetime.datetime.now(),
        gps_lat=gps_lat,
        gps_lng=gps_lng,
        store_id=store_id,
        execution_time=execution_time
    )
    session_main.add(submission)
    session_main.commit()
    session_main.close()


@app.route('/categories', methods=['POST'])
@app.route('/v2/categories', methods=['POST'])
@multi_auth.login_required
def api_categories():

    try:
        start = time.time()
        session = Session()

        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' /v2/categories:')
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

        sql_query = 'select *, (select id from user_categories_disabled where user_id = "' + str(g.user_id) + '" and category = deals.categories.category limit 1) as disabled from deals.categories where id > 0 order by id'

        item_info = session.execute(sql_query)
        session.close()
        item_info = list(item_info)

        output = {}
        categories_list = []

        for row in item_info:

            category_record = {}
            if row.id is not None:
                category_record['category'] = str(row.category)

                image = row.image
                category_record['image'] = 'https://www.topsavings.com/static/top_categories/' + str(image)

                is_disabled = row.disabled
                if is_disabled is None:
                    category_record['is_enabled'] = True
                else:
                    category_record['is_enabled'] = False

                categories_list.append(category_record)

        output['categories'] = categories_list

        result = json.dumps(output)

        end = time.time()

        execution_time = end - start
        p_api_act = threading.Thread(target=record_api_activity,args=(g.user_id, gps_lat, gps_lng, '/v2/categories', str(get_user_ip()), execution_time))
        p_api_act.start()

        print('Execution time (/v2/categories): %s' % (end - start))

        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/v2/categories', error_message)
        return False


@app.route('/top_categories', methods=['POST'])
@app.route('/v2/top_categories', methods=['POST'])
@multi_auth.login_required
def api_top_categories():

    try:
        start = time.time()
        session = Session()

        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' /v2/top_categories:')
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

        sql_query = 'select *, (select id from user_categories_disabled where user_id = "' + str(g.user_id) + '" and category = deals.categories.category limit 1) as disabled from deals.categories where id > 0 order by id'

        item_info = session.execute(sql_query)

        item_info = list(item_info)

        output = {}
        categories_list = []

        for row in item_info:

            category_record = {}
            if row.id is not None:
                category_record['category'] = str(row.category)

                image = row.image
                category_record['image'] = 'https://www.topsavings.com/static/top_categories/' + str(image)

                category_record['alpha'] = 0.13
                categories_list.append(category_record)

        output['categories'] = categories_list

        result = json.dumps(output)

        session.close()

        end = time.time()

        execution_time = end - start
        p_api_act = threading.Thread(target=record_api_activity,args=(g.user_id, gps_lat, gps_lng, '/v2/top_categories', str(get_user_ip()), execution_time))
        p_api_act.start()

        print('Execution time (/v2/top_categories): %s' % (end - start))

        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/v2/top_categories', error_message)
        return False


@app.route('/v2/set_category', methods=['POST'])
@multi_auth.login_required
def api_set_category():
    try:
        start = time.time()
        session = Session()
        session_main = Session_main()
        session_deals = Session_deals()
        print(
            str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(g.user_id) + ' /set_category:')
        try:
            submission = request.get_json()

        except Exception as e:
            print(e)
            email_crash_report('/set_category', e)
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

        if 'category' in submission:
            category = submission['category']
        else:
            result = '{"status": "missing category : string"}'
            return Response(result, mimetype="application/json")

        if 'is_enabled' in submission:
            is_enabled = submission['is_enabled']
        else:
            result = '{"status": "missing is_enabled : boolean"}'
            return Response(result, mimetype="application/json")

        get_category = session_deals.query(models.categories).filter(
            (models.categories.category == category)
        ).first()

        if get_category:
            category_id = get_category.id
        else:
            result = '{"invalid category"}'
            return Response(result, mimetype="application/json")

        if is_enabled is True:
            sql_query = 'delete from user_categories_disabled where user_id = ' + str(g.user_id) + ' and category = "' + str(category) + '"'
            result = '{"status": "enabled"}'
        elif is_enabled is False:
            sql_query = 'insert into user_categories_disabled(user_id, category) values(' + str(g.user_id) + ', "' + str(category) + '")'
            result = '{"status": "disabled"}'

        session.execute(sql_query)
        session.commit()
        session.close()

        session_main.execute(sql_query)
        session_main.commit()
        session_main.close()

        end = time.time()
        execution_time = end - start

        p_api_act = threading.Thread(target=record_api_activity, args=(
            g.user_id, gps_lat, gps_lng, '/v2/set_category', str(get_user_ip()), execution_time))
        p_api_act.start()

        print('Execution time (/v2/set_category): %s' % (end - start))
        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/v2/set_category', error_message)
        return False


