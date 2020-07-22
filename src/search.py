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
import unidecode

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from settings import SMTP_SERVER
from settings import SMTP_PORT
from settings import SMTP_LOGIN
from settings import SMTP_PASSWORD

from src.authentication import multi_auth
from src.email import email_crash_report

from src.utils import get_user_ip
from src.utils import check_gps
from src.utils import record_api_activity

from src.stores import get_current_store
from src.prices import get_prices

from settings import S3_ENDPOINT
from settings import PRODUCT_IMAGE_BUCKET_NAME
from settings import STORE_IMAGE_BUCKET

from settings import SAVINGS_MIN
from settings import SAVINGS_MIN_PERCENT


@app.route('/v2/search_default', methods=['GET', 'POST'])
@app.route('/search_default', methods=['GET', 'POST'])
@multi_auth.login_required
def search_default():
    try:
        start = time.time()
        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(
            g.user_id) + ' /search_default:')

        try:
            submission = request.get_json()

        except Exception as e:
            print(e)
            email_crash_report('/search_default', e)

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

        result = '{"title": "Popular Items", "query_items":["Bread", "Breakfast", "Butter", "Margarine", "Candy & Chocolate","Cheese", "Chips & Snacks", "Coffee", "Cookies", "Crackers", "Desserts", "Eggs", "Frozen Food", "Juice", "Milk", "Pasta", "Pizza", "Rice", "Sauces", "Soda", "Tea", "Toilet Paper", "Yogurt"]}'

        end = time.time()
        execution_time = end - start

        print('Execution time (/search_default): ' + str(execution_time))
        # result = json.dumps(output)
        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/search_default', error_message)
        return False


@app.route('/v2/search_suggestions', methods=['GET', 'POST'])
@app.route('/search_suggestions', methods=['GET', 'POST'])
@multi_auth.login_required
def search_suggestions():
    try:
        start = time.time()
        print(str(datetime.datetime.now()) + ' IP:' + str(get_user_ip()) + ' user_id:' + str(
            g.user_id) + ' /search_suggestions:')

        try:
            submission = request.get_json()
        except Exception as e:
            print(e)
            email_crash_report('/search_suggestions', e)

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

        if 'query' in submission:
            query = submission['query']
            query = query.replace("’", "'")
            query = query.replace("´", "'")

            query = query.replace("\xe2\x80\x99", "'")
            query = query.strip()

            query = re.sub(r'[^a-zA-Z ]', '', query)
            query = query.lower()

        else:
            result = '{"status": "missing query: string"}'
            return Response(result, mimetype="application/json")

        print('QUERY ' + str(query))

        if query is None or query == '':
            result = '{"title": "Suggestions", "query_items":["Bread", "Breakfast", "Butter", "Margarine", "Candy & Chocolate","Cheese", "Chips & Snacks", "Coffee", "Cookies", "Crackers", "Desserts", "Eggs", "Frozen Food", "Juice", "Milk", "Pasta", "Pizza", "Rice", "Sauces", "Soda", "Tea", "Toilet Paper", "Yogurt"]}'

            end = time.time()
            execution_time = end - start

            print('Execution time (/search_suggestions): ' + str(execution_time))
            # result = json.dumps(output)
            return Response(result, mimetype="application/json")

        sql_query = 'select distinct search_query from (select case when item_info.prod_name like CONCAT("%", item_info.brand ,"%") then item_info.prod_name else CONCAT(item_info.brand, " ", item_info.prod_name) END  as search_query, search_length from item_info where (lcase(item_info.brand) like "' + query + '%" or lcase(item_info.prod_name) like "' + query + '%")  and item_info.omit_from_search is null and item_info.prod_name NOT LIKE "%condom%" AND item_info.prod_name NOT LIKE "%lubricant%" AND item_info.prod_name NOT LIKE "%pregnan%" AND item_info.prod_name NOT LIKE "%ovula%"  and exists (select * from scans where prod_id = item_info.prod_id and price is not null and scans.expiry > now()) order by search_length limit 30) t1'

        session = Session()
        item_info = session.execute(sql_query)

        item_info = list(item_info)
        session.close()
        query_items = []
        output = {}
        for row in item_info:
            search_query = row.search_query
            if row.search_query != '' and row.search_query is not None:
                query_items.append(search_query)

        output['title'] = 'Suggestions'
        output['query_items'] = query_items

        result = json.dumps(output)

        end = time.time()

        print('Execution time (search_suggestions): %s' % (end - start))

        print(result)
        return Response(result, mimetype="application/json")

    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' Error in ' + str(fname) + ' on line ' + str(exc_tb.tb_lineno)
        email_crash_report('/search_suggestions', error_message)
        return False


@app.route('/v2/search', methods=['POST', 'GET'])
@multi_auth.login_required
def api_search_v2():
    try:
        start = time.time()
        session = Session()

        search_list_json = []

        ipaddress = get_user_ip()

        print(str(datetime.datetime.now()) + ' IP:' + str(ipaddress) + ' user_id:' + str(g.user_id) + ' /v2/search:')
        try:
            submission = request.get_json()
            print(submission)

        except Exception as e:
            print(e)
            email_crash_report('/v2/search', e)
            result = '{"status": "MUST BE IN JSON FORMAT"}'
            return Response(result, mimetype="application/json")

        if 'gps' in submission:
            gps = submission['gps']
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

        if 'query' in submission:
            query = submission['query']

            query = query.strip()

            if query == '' or query is None:
                result = '{}'
                return Response(result, mimetype="application/json")

            query_submitted = query

            if query is not None:

                query = query.strip()
                query = query.lower()

                smart_product = query

                query = query.replace(" and ", " ")
                query = query.replace("’", "")
                query = query.replace("´", "")
                query = query.replace("-", "")
                query = query.replace("%", " ")
                query = query.replace("\xe2\x80\x99", "")

                query = re.sub(r'[^a-zA-Z ]', '', query)

                query = query.strip()
                query = unidecode.unidecode(query)

                if query is None or query == '':
                    result = '{"status": "bad query"}'
                    return Response(result, mimetype="application/json")
        else:
            result = '{"status": "missing query: string"}'
            return Response(result, mimetype="application/json")

        if 'page' in submission:
            page_size = 20
            page = submission['page']
            page = int(page)
            if page is None or page == '':
                page = 0
            start_record = int(page)
            start_record = start_record * page_size

        else:
            result = '{"status": "missing page: integer starting at 0"}'
            return Response(result, mimetype="application/json")

        current_store_info = get_current_store(gps_lat, gps_lng)
        current_store_id = current_store_info['current_store_id']

        str_sql = 'select chain from stores_search where query = "' + str(query) + '"'

        store_check = session.execute(str_sql)
        store_check_status = False
        for row in store_check:
            if row.chain is not None:
                store_check_status = True
                store_check_chain = row.chain

        if not store_check_status:

            if page == 0:

                generic_search = session.query(models.shopping_list).filter(
                    (models.shopping_list.user_id == g.user_id) &
                    (models.shopping_list.generic_name == query)
                ).first()

                if not generic_search and len(smart_product) < 15:
                    search_list_record = {}
                    search_list_record['prod_id'] = None
                    search_list_record['prod_name'] = None
                    search_list_record['image'] = None
                    search_list_record['image_thumb'] = None
                    search_list_record['is_in_shopping_list'] = False
                    search_list_record['nutr_score'] = None
                    search_list_record['nutr_info'] = None
                    search_list_record['size'] = None
                    search_list_record['prices'] = []
                    search_list_record['bg_colour'] = '#B1B1B110'
                    search_list_record['generic_name'] = smart_product
                    search_list_record['icon'] = 'https://www.topsavings.com/static/shopping_list_icons/smart_product.png'
                    search_list_record[
                        'icon_light'] = 'https://www.topsavings.com/static/smart_icons_light/smart_product.png'
                    search_list_json.append(search_list_record)

                search_sql_generic = 'select * from shopping_list_generic, shopping_list_generic_search_tags where shopping_list_generic.name = shopping_list_generic_search_tags.generic_name and shopping_list_generic_search_tags.generic_name is not null and (shopping_list_generic_search_tags.tag = "' + str(smart_product) + '" or shopping_list_generic_search_tags.generic_name = "' + str(smart_product) + '") and not exists (select * from shopping_list where generic_name = shopping_list_generic.name and shopping_list_generic.rank is not null and expired is null and user_id = "' + str(g.user_id) + '") order by RAND() limit 3'

                item_info_generic = session.execute(search_sql_generic)

                session.close()

                for row in item_info_generic:

                    if row.name is not None:
                        search_list_record = {}
                        search_list_record['prod_id'] = None
                        search_list_record['prod_name'] = None
                        search_list_record['image'] = None
                        search_list_record['image_thumb'] = None
                        search_list_record['is_in_shopping_list'] = False
                        search_list_record['nutr_score'] = None
                        search_list_record['nutr_info'] = None
                        search_list_record['size'] = None
                        search_list_record['prices'] = []
                        search_list_record['bg_colour'] = '#B1B1B110'
                        search_list_record['generic_name'] = row.name
                        search_list_record['icon'] = 'https://www.topsavings.com/static/shopping_list_icons/' + str(row.icon)
                        search_list_record['icon_light'] = 'https://www.topsavings.com/static/smart_icons_light/' + str(row.icon)
                        search_list_json.append(search_list_record)

            sql_query = 'select prod_id from search.queries where query = "' + query + '" limit 1'

            item_info = session.execute(sql_query)
            search_exists = False
            for row in item_info:
                if row.prod_id is not None:
                    search_exists = True

            if search_exists is True:

                search_sql = 'SELECT distinct item_info.prod_id, item_info.awaiting_approval, item_info.brand, item_info.prod_name, item_info.quantity AS size_quantity, item_info.quantity_units, item_info.size, item_info.units as size_units, item_info.image, (select quantity from shopping_list where user_id = "' + str(g.user_id) + '" and prod_id = item_info.prod_id limit 1) as quantity FROM search.queries, item_info WHERE search.queries.query = "' + query + '"  AND search.queries.prod_id = item_info.prod_id AND item_info.omit_from_search IS NULL and exists (select scan_id from scans, stores where scans.expiry > now() and scans.price is not null and prod_id = item_info.prod_id and stores.id = scans.store_id AND (st_distance_sphere(stores.pt, point(' + gps_lng + ', ' + gps_lat + ')) <= ' + str(g.distance) + ' or stores.online = 1)) limit ' + str(start_record) + ', ' + str(page_size)

            else:

                if page == 0:
                    p_cache_search = threading.Thread(target=cache_search_v2, args=(query,))
                    p_cache_search.start()

                where_str = '('
                for word in query.split():
                    word = word.rstrip('s')
                    word = word.strip()

                    if where_str != '(':
                        where_str = where_str + ' or '

                    where_str = where_str + ' item_info.brand_searchable like "% ' + word + ' %" or item_info.prod_name_searchable like "% ' + word + ' %"'

                where_str = where_str + ')'

                search_sql = 'SELECT distinct item_info.prod_id, item_info.awaiting_approval, item_info.brand, item_info.prod_name, item_info.quantity AS size_quantity, item_info.quantity_units, item_info.size, item_info.units as size_units, item_info.image, (select quantity from shopping_list where user_id = "' + str( g.user_id) + '" and prod_id = item_info.prod_id limit 1) as quantity FROM item_info WHERE ' + where_str + '  AND item_info.omit_from_search IS NULL and exists (select scan_id from scans, stores where scans.expiry > now() and scans.price is not null and prod_id = item_info.prod_id and stores.id = scans.store_id AND (st_distance_sphere(stores.pt, point(' + gps_lng + ', ' + gps_lat + ')) <= ' + str(g.distance) + ' or stores.online = 1)) limit ' + str(start_record) + ', ' + str(page_size)

        else:

            search_sql = 'select *, null as query_count, null as word_count, null as word_count_unique from (select distinct id, date_time, prod_id, prod_name, brand, category, size, size_units, size_quantity, quantity_units, chain, store_id, price, savings_price, savings_percent, quantity_sl, image, awaiting_approval, logo, quantity, units, (select category from deals.categories where id = d1.category limit 1) as category_text from deals.deals as d1 where NOT EXISTS (SELECT * FROM user_categories_disabled, search_tags WHERE lcase(user_categories_disabled.category) = lcase(search_tags.tag) and search_tags.prod_id = d1.prod_id and user_categories_disabled.user_id = ' + str(g.user_id) + ') and category is not null and user_id = ' + str(g.user_id) + ' and lower(chain) = "' + store_check_chain + '")t1 left join (select category as category_id, count(*) as category_size from deals.deals where user_id = ' + str(g.user_id) + ' and category is not null and lower(chain) = "' + store_check_chain + '" group by category) cat1 on cat1.category_id = t1.category order by savings_percent desc, savings_price desc, price limit ' + str(start_record) + ', ' + str(page_size)

        print(search_sql)
        print('live search')

        item_info = session.execute(search_sql)

        item_info = list(item_info)
        session.close()

        for row in item_info:

            search_list_record = {}
            if row.prod_id is None:
                search_list_record['prod_id'] = None

            else:
                prod_id = row.prod_id
                search_list_record['prod_id'] = str(row.prod_id)

            if row.image is None:
                search_list_record[
                    'image'] = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/no_image_grocery_lg.png'
                search_list_record[
                    'image_thumb'] = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/no_image_grocery_sm.png'
            else:
                if row.awaiting_approval is None:
                    search_list_record[
                        'image'] = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME + '/sm_new/' + str(
                        row.image)
                    search_list_record[
                        'image_thumb'] = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME + '/sm_new/' + str(
                        row.image)

                else:
                    search_list_record['image'] = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME + '/sm_new/' + str(row.image)
                    search_list_record['image_thumb'] = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME + '/sm_new/' + str(row.image)

            if row.quantity is None:
                search_list_record['is_in_shopping_list'] = False
            else:
                search_list_record['is_in_shopping_list'] = True

            # todo update nutrition

            search_list_record['nutr_score'] = None
            search_list_record['nutr_info'] = None

            if row.size is None:
                size = None
            else:
                size = str(row.size)

                if row.size_units is None:
                    units = None
                else:

                    units = str(row.size_units)
                    units = units.lower()
                    if units == 'g' or units == 'kg':
                        size = size + str(row.size_units)
                    else:
                        size = size + ' ' + str(row.size_units)

                if row.size_quantity is not None and row.quantity_units is None:
                    size_quantity = row.size_quantity

                    size = str(size_quantity) + ' X ' + str(size)

            search_list_record['size'] = size

            if row.prod_name is None:

                search_list_record['prod_name'] = None
            else:
                # search_list_record['name'] = unicode(row.prod_name, errors='ignore')
                prod_name = row.prod_name

                brand = row.brand

                if brand is not None and brand != '':
                    if brand.lower() not in prod_name.lower():
                        prod_name = brand + ' ' + prod_name

                # if size is not None:
                #   prod_name = prod_name + ' ' + size

                search_list_record['prod_name'] = prod_name

            all_prices = get_prices(prod_id, gps_lat, gps_lng, current_store_id)
            prices = all_prices['prices']
            # prices = []

            search_list_record['prices'] = prices

            saving_price = all_prices['saving_price']
            best_price = all_prices['price']
            if best_price is None:
                best_price = 0

            if saving_price is None:
                saving_price = 0

            if saving_price > 0 and best_price > 0:
                save_ratio = saving_price / (saving_price + best_price)
                save_ratio = save_ratio * 100
                save_ratio = int(save_ratio)
            else:
                save_ratio = 0

            if save_ratio > 49 and save_ratio < 75:
                search_list_record['crest_color'] = '#fa0000'
                search_list_record['crest_text'] = str(save_ratio) + '% OFF'
                search_list_record['promo_color'] = '#fa0000'
                search_list_record['promo_text'] = str(save_ratio) + '% OFF'
            elif save_ratio > 24:
                search_list_record['crest_color'] = '#fa7000'
                search_list_record['crest_text'] = str(save_ratio) + '% OFF'
                search_list_record['promo_color'] = '#fa7000'
                search_list_record['promo_text'] = str(save_ratio) + '% OFF'

            elif saving_price > 1:
                saving_price_disp = '{0:.2f}'.format(saving_price)
                search_list_record['crest_color'] = '#4cd96d'
                search_list_record['crest_text'] = 'Save $' + str(saving_price_disp)
                search_list_record['promo_color'] = '#4cd96d'
                search_list_record['promo_text'] = 'Save $' + str(saving_price_disp)
            else:
                search_list_record['crest_color'] = None
                search_list_record['crest_text'] = None
                search_list_record['promo_color'] = None
                search_list_record['promo_text'] = None

            search_list_record['generic_name'] = None
            search_list_record['icon'] = None


            search_list_json.append(search_list_record)

        submission = models.search(
            query=query_submitted,
            page=page,
            time=datetime.datetime.now(),
            user_id=int(g.user_id),
            gps_lat=gps_lat,
            gps_lng=gps_lng
        )
        session_main = Session_main()
        session_main.add(submission)
        session_main.commit()
        search_id = submission.id
        session_main.close()

        output_record = {}

        output_record['list'] = search_list_json

        result = json.dumps(output_record)

        session.close()

        end = time.time()

        execution_time = end - start

        p_api_act = threading.Thread(target=record_api_activity, args=(g.user_id, gps_lat, gps_lng, '/v2/search', str(ipaddress), execution_time), kwargs={'search_id': search_id, 'user_activity': 1})
        p_api_act.start()

        if g.user_id > 5 and page == 0:
            p_report_search = threading.Thread(target=report_search, args=(query, gps_lat, gps_lng, execution_time))
            p_report_search.start()

        end = time.time()

        print('Execution time (/v2/search): %s' % (end - start))
        return Response(result, mimetype="application/json")
    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' ' + str(fname) + ' ' + str(exc_tb.tb_lineno)
        email_crash_report('/v2/search', error_message)
        return False


def cache_search_v2(query):
    try:
        print('CACHE SEARCH ')
        start = time.time()
        session = Session()

        range = '1000000'
        gps_lat = '45.424068'
        gps_lng = '-75.698929'

        query = query.strip()
        query = query.lower()
        query = query.replace(" and ", " ")
        query = query.replace("’", "")
        query = query.replace("´", "")
        query = query.replace("-", "")
        query = query.replace("%", " ")
        query = query.replace("\xe2\x80\x99", "")
        query = re.sub(r'[^a-zA-Z0-9 ]', '', query)
        query = query.strip()
        query = unidecode.unidecode(query)

        sql_query = 'select prod_id from search.queries where query = "' + query + '" limit 1'

        item_info = session.execute(sql_query)
        deals_exist = False
        for row in item_info:
            if row.prod_id is not None:
                deals_exist = True

        if deals_exist is False:

            print('Cache search for ' + str(query))

            query_word_count = 0

            query_double_metaphone_count = 0

            word_count_query = ', ('
            double_metaphone_count_query = ', ('
            double_metaphone_count_unique_query = ', ('
            double_metaphone_where_query = '('
            for word in query.split():
                dm_word = re.sub(r'[^a-zA-Z0-9]', '', word)
                word = word.rstrip('s')
                word = word.strip()

                if len(word) > 0:
                    double_metaphone_pri = dm(word)[0]

                    if query_double_metaphone_count > 0:
                        double_metaphone_count_query = double_metaphone_count_query + ' + '
                        double_metaphone_count_unique_query = double_metaphone_count_unique_query + ' + '

                    if len(double_metaphone_pri) > 0:
                        double_metaphone_count_query = double_metaphone_count_query + 'substrCount(item_info.double_metaphone,"' + double_metaphone_pri + '")'

                        double_metaphone_count_unique_query = double_metaphone_count_unique_query + 'substrCheckV2(item_info.double_metaphone,"' + double_metaphone_pri + '")'

                        if query_double_metaphone_count > 0:
                            double_metaphone_where_query = double_metaphone_where_query + ' or '

                        double_metaphone_where_query = double_metaphone_where_query + 'item_info.double_metaphone like "% ' + double_metaphone_pri + ' %"'

                        query_double_metaphone_count = query_double_metaphone_count + 1

                if query_word_count > 0:
                    word_count_query = word_count_query + ' + '

                word_count_query = word_count_query + 'substrCount(item_info.prod_name_searchable,lcase("' + word + '"))'

                word_count_query = word_count_query + ' + substrCount(item_info.brand_searchable,lcase("' + word + '"))'

                query_word_count = query_word_count + 1

            word_count_query = word_count_query + ') as word_count '

            double_metaphone_count_query = double_metaphone_count_query + ') as double_metaphone_count'
            double_metaphone_count_unique_query = double_metaphone_count_unique_query + ') as double_metaphone_count_unique'
            double_metaphone_where_query = double_metaphone_where_query + ')'

            query_word_count = 0

            word_count_query = word_count_query + ', ('
            for word in query.split():
                word = word.rstrip('s')
                if query_word_count > 0:
                    word_count_query = word_count_query + ' + '

                word_count_query = word_count_query + 'substrCheck(item_info.prod_name_searchable, item_info.brand_searchable,lcase("' + word + '"))'

                query_word_count = query_word_count + 1

            word_count_query = word_count_query + ') as word_count_unique'

            search_sql = 'insert into search.queries (query, prod_id, ranking) select "' + str(
                query) + '" as query, prod_id, @rownum := @rownum + 1 as row_number from (SELECT distinct item_info.prod_id, item_info.awaiting_approval, item_info.brand, item_info.prod_name, item_info.quantity AS size_quantity, item_info.quantity_units, item_info.size, item_info.units, search_tags.rank, item_info.image, NULL AS query_count, NULL AS word_count, NULL AS word_count_unique, NULL AS double_metaphone_count, NULL AS double_metaphone_count_unique, (SELECT min(unit_price) FROM scans, stores WHERE scans.prod_id = item_info.prod_id AND scans.expiry > now() and ( scans.start <= now() or scans.start is null ) AND stores.id = scans.store_id AND (st_distance_sphere(stores.pt, point(' + gps_lng + ', ' + gps_lat + ')) <= ' + str(range) + ' or stores.online = 1)) AS unit_price, null as quantity FROM search_tags, item_info WHERE search_tags.tag = "' + query + '"  AND search_tags.prod_id IS NOT NULL AND search_tags.prod_id = item_info.prod_id AND item_info.omit_from_search IS NULL UNION ALL SELECT item_info.prod_id, item_info.awaiting_approval, item_info.brand, item_info.prod_name, item_info.quantity AS size_quantity, item_info.quantity_units, item_info.size, item_info.units, NULL AS rank, item_info.image, (substrcount(lcase(item_info.brand_searchable), "' + query + '") + substrcount(lcase(item_info.prod_name_searchable), "' + query + '")) AS query_count ' + word_count_query + double_metaphone_count_query + double_metaphone_count_unique_query + ', ( SELECT min(unit_price) FROM scans, stores WHERE scans.prod_id = item_info.prod_id AND scans.expiry > now() and ( scans.start <= now() or scans.start is null ) AND (stores.id = scans.store_id AND st_distance_sphere(stores.pt, point(' + gps_lng + ', ' + gps_lat + ')) <= ' + str(range) + ' or stores.online = 1)) AS unit_price, null as quantity FROM item_info WHERE item_info.omit_from_search IS NULL and ' + double_metaphone_where_query + ' AND NOT EXISTS (SELECT 1 FROM search_tags WHERE tag = "' + query + '" and search_tags.prod_id = item_info.prod_id ) AND NOT EXISTS (SELECT 1 FROM search_locked WHERE tag = "' + query + '") ORDER BY CASE WHEN unit_price IS NOT NULL AND rank IS NOT NULL THEN - rank END DESC, CASE WHEN unit_price IS NOT NULL AND rank IS NOT NULL THEN - unit_price END DESC, CASE WHEN rank IS NULL AND unit_price IS NOT NULL THEN query_count END DESC, CASE WHEN rank IS NULL AND unit_price IS NOT NULL THEN word_count_unique END DESC, CASE WHEN rank IS NULL AND unit_price IS NOT NULL THEN double_metaphone_count_unique END DESC, CASE WHEN rank IS NULL AND unit_price IS NOT NULL THEN word_count END DESC, CASE WHEN rank IS NULL AND unit_price IS NOT NULL THEN double_metaphone_count END DESC, CASE WHEN rank IS NULL AND unit_price IS NULL THEN query_count END DESC, CASE WHEN rank IS NULL AND unit_price IS NULL THEN word_count_unique END DESC, CASE WHEN rank IS NULL AND unit_price IS NULL THEN double_metaphone_count_unique END DESC, CASE WHEN rank IS NULL AND unit_price IS NULL THEN word_count END DESC, CASE WHEN rank IS NULL AND unit_price IS NULL THEN double_metaphone_count END DESC, - unit_price desc limit 500)t1 cross join (select @rownum := 0) r'

            print(search_sql)

            remove_old_sql = 'delete from search.queries where query = "' + query + '"'

            session.execute(remove_old_sql)
            session.commit()
            session.execute(search_sql)
            session.commit()

        session.close()

        end = time.time()

        execution_time = end - start

        print('Execution time for "' + str(query) + '" > ' + str(execution_time) + ' seconds')

    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        raise Exception("Fix this now")


def dm(st):
    # double metaphone https://en.wikipedia.org/wiki/Metaphone#Double_Metaphone  algo from https://github.com/dracos/double-metaphone/blob/master/metaphone.py
    """dm(string) -> (string, string or None)
	returns the double metaphone codes for given string - always a tuple
	there are no checks done on the input string, but it should be a single	word or name."""
    vowels = ['A', 'E', 'I', 'O', 'U', 'Y']
    ##st = st.decode('utf-8', 'ignore')
    st = st.upper()  # st is short for string. I usually prefer descriptive over short, but this var is used a lot!
    is_slavo_germanic = (st.find('W') > -1 or st.find('K') > -1 or st.find('CZ') > -1 or st.find(
        'WITZ') > -1)
    length = len(st)
    first = 2
    st = ('-') * first + st + (
            ' ' * 5)  # so we can index beyond the begining and end of the input string
    last = first + length - 1
    pos = first  # pos is short for position
    pri = sec = ''  # primary and secondary metaphone codes
    # skip these silent letters when at start of word
    if st[first:first + 2] in ["GN", "KN", "PN", "WR", "PS"]:
        pos += 1
    # Initial 'X' is pronounced 'Z' e.g. 'Xavier'
    if st[first] == 'X':
        pri = sec = 'S'  # 'Z' maps to 'S'
        pos += 1
    # main loop through chars in st
    while pos <= last:
        # print str(pos) + '\t' + st[pos]
        ch = st[pos]  # ch is short for character
        # nxt (short for next characters in metaphone code) is set to  a tuple of the next characters in
        # the primary and secondary codes and how many characters to move forward in the string.
        # the secondary code letter is given only when it is different than the primary.
        # This is just a trick to make the code easier to write and read.
        nxt = (None, 1)  # default action is to add nothing and move to next char
        if ch in vowels:
            nxt = (None, 1)
            if pos == first:  # all init vowels now map to 'A'
                nxt = ('A', 1)
        elif ch == 'B':
            # "-mb", e.g", "dumb", already skipped over... see 'M' below
            if st[pos + 1] == 'B':
                nxt = ('P', 2)
            else:
                nxt = ('P', 1)
        elif ch == 'C':
            # various germanic
            if (pos > (first + 1) and st[pos - 2] not in vowels and st[pos - 1:pos + 2] == 'ACH' and \
                    (st[pos + 2] not in ['I', 'E'] or st[pos - 2:pos + 4] in ['BACHER', 'MACHER'])):
                nxt = ('K', 2)
            # special case 'CAESAR'
            elif pos == first and st[first:first + 6] == 'CAESAR':
                nxt = ('S', 2)
            elif st[pos:pos + 4] == 'CHIA':  # italian 'chianti'
                nxt = ('K', 2)
            elif st[pos:pos + 2] == 'CH':
                # find 'michael'
                if pos > first and st[pos:pos + 4] == 'CHAE':
                    nxt = ('K', 'X', 2)
                elif pos == first and (st[pos + 1:pos + 6] in ['HARAC', 'HARIS'] or \
                                       st[pos + 1:pos + 4] in ["HOR", "HYM", "HIA", "HEM"]) and st[
                                                                                                first:first + 5] != 'CHORE':
                    nxt = ('K', 2)
                # germanic, greek, or otherwise 'ch' for 'kh' sound
                elif st[first:first + 4] in ['VAN ', 'VON '] or st[first:first + 3] == 'SCH' \
                        or st[pos - 2:pos + 4] in ["ORCHES", "ARCHIT", "ORCHID"] \
                        or st[pos + 2] in ['T', 'S'] \
                        or ((st[pos - 1] in ["A", "O", "U", "E"] or pos == first) \
                            and st[pos + 2] in ["L", "R", "N", "M", "B", "H", "F", "V", "W", " "]):
                    nxt = ('K', 1)
                else:
                    if pos > first:
                        if st[first:first + 2] == 'MC':
                            nxt = ('K', 2)
                        else:
                            nxt = ('X', 'K', 2)
                    else:
                        nxt = ('X', 2)
            # e.g, 'czerny'
            elif st[pos:pos + 2] == 'CZ' and st[pos - 2:pos + 2] != 'WICZ':
                nxt = ('S', 'X', 2)
            # e.g., 'focaccia'
            elif st[pos + 1:pos + 4] == 'CIA':
                nxt = ('X', 3)
            # double 'C', but not if e.g. 'McClellan'
            elif st[pos:pos + 2] == 'CC' and not (pos == (first + 1) and st[first] == 'M'):
                # 'bellocchio' but not 'bacchus'
                if st[pos + 2] in ["I", "E", "H"] and st[pos + 2:pos + 4] != 'HU':
                    # 'accident', 'accede' 'succeed'
                    if (pos == (first + 1) and st[first] == 'A') or \
                            st[pos - 1:pos + 4] in ['UCCEE', 'UCCES']:
                        nxt = ('KS', 3)
                    # 'bacci', 'bertucci', other italian
                    else:
                        nxt = ('X', 3)
                else:
                    nxt = ('K', 2)
            elif st[pos:pos + 2] in ["CK", "CG", "CQ"]:
                nxt = ('K', 'K', 2)
            elif st[pos:pos + 2] in ["CI", "CE", "CY"]:
                # italian vs. english
                if st[pos:pos + 3] in ["CIO", "CIE", "CIA"]:
                    nxt = ('S', 'X', 2)
                else:
                    nxt = ('S', 2)
            else:
                # name sent in 'mac caffrey', 'mac gregor
                if st[pos + 1:pos + 3] in [" C", " Q", " G"]:
                    nxt = ('K', 3)
                else:
                    if st[pos + 1] in ["C", "K", "Q"] and st[pos + 1:pos + 3] not in ["CE", "CI"]:
                        nxt = ('K', 2)
                    else:  # default for 'C'
                        nxt = ('K', 1)
        elif ch == u'Ç':
            nxt = ('S', 1)
        elif ch == 'D':
            if st[pos:pos + 2] == 'DG':
                if st[pos + 2] in ['I', 'E', 'Y']:  # e.g. 'edge'
                    nxt = ('J', 3)
                else:
                    nxt = ('TK', 2)
            elif st[pos:pos + 2] in ['DT', 'DD']:
                nxt = ('T', 2)
            else:
                nxt = ('T', 1)
        elif ch == 'F':
            if st[pos + 1] == 'F':
                nxt = ('F', 2)
            else:
                nxt = ('F', 1)
        elif ch == 'G':
            if st[pos + 1] == 'H':
                if pos > first and st[pos - 1] not in vowels:
                    nxt = ('K', 2)
                elif pos < (first + 3):
                    if pos == first:  # 'ghislane', ghiradelli
                        if st[pos + 2] == 'I':
                            nxt = ('J', 2)
                        else:
                            nxt = ('K', 2)
                # Parker's rule (with some further refinements) - e.g., 'hugh'
                elif (pos > (first + 1) and st[pos - 2] in ['B', 'H', 'D']) \
                        or (pos > (first + 2) and st[pos - 3] in ['B', 'H', 'D']) \
                        or (pos > (first + 3) and st[pos - 4] in ['B', 'H']):
                    nxt = (None, 2)
                else:
                    # e.g., 'laugh', 'McLaughlin', 'cough', 'gough', 'rough', 'tough'
                    if pos > (first + 2) and st[pos - 1] == 'U' \
                            and st[pos - 3] in ["C", "G", "L", "R", "T"]:
                        nxt = ('F', 2)
                    else:
                        if pos > first and st[pos - 1] != 'I':
                            nxt = ('K', 2)
            elif st[pos + 1] == 'N':
                if pos == (first + 1) and st[first] in vowels and not is_slavo_germanic:
                    nxt = ('KN', 'N', 2)
                else:
                    # not e.g. 'cagney'
                    if st[pos + 2:pos + 4] != 'EY' and st[pos + 1] != 'Y' and not is_slavo_germanic:
                        nxt = ('N', 'KN', 2)
                    else:
                        nxt = ('KN', 2)
            # 'tagliaro'
            elif st[pos + 1:pos + 3] == 'LI' and not is_slavo_germanic:
                nxt = ('KL', 'L', 2)
            # -ges-,-gep-,-gel-, -gie- at beginning
            elif pos == first and (st[pos + 1] == 'Y' \
                                   or st[pos + 1:pos + 3] in ["ES", "EP", "EB", "EL", "EY", "IB",
                                                              "IL", "IN", "IE", "EI", "ER"]):
                nxt = ('K', 'J', 2)
            # -ger-,  -gy-
            elif (st[pos + 1:pos + 2] == 'ER' or st[pos + 1] == 'Y') \
                    and st[first:first + 6] not in ["DANGER", "RANGER", "MANGER"] \
                    and st[pos - 1] not in ['E', 'I'] and st[pos - 1:pos + 2] not in ['RGY', 'OGY']:
                nxt = ('K', 'J', 2)
            # italian e.g, 'biaggi'
            elif st[pos + 1] in ['E', 'I', 'Y'] or st[pos - 1:pos + 3] in ["AGGI", "OGGI"]:
                # obvious germanic
                if st[first:first + 4] in ['VON ', 'VAN '] or st[first:first + 3] == 'SCH' \
                        or st[pos + 1:pos + 3] == 'ET':
                    nxt = ('K', 2)
                else:
                    # always soft if french ending
                    if st[pos + 1:pos + 5] == 'IER ':
                        nxt = ('J', 2)
                    else:
                        nxt = ('J', 'K', 2)
            elif st[pos + 1] == 'G':
                nxt = ('K', 2)
            else:
                nxt = ('K', 1)
        elif ch == 'H':
            # only keep if first & before vowel or btw. 2 vowels
            if (pos == first or st[pos - 1] in vowels) and st[pos + 1] in vowels:
                nxt = ('H', 2)
            else:  # (also takes care of 'HH')
                nxt = (None, 1)
        elif ch == 'J':
            # obvious spanish, 'jose', 'san jacinto'
            if st[pos:pos + 4] == 'JOSE' or st[first:first + 4] == 'SAN ':
                if (pos == first and st[pos + 4] == ' ') or st[first:first + 4] == 'SAN ':
                    nxt = ('H',)
                else:
                    nxt = ('J', 'H')
            elif pos == first and st[pos:pos + 4] != 'JOSE':
                nxt = ('J', 'A')  # Yankelovich/Jankelowicz
            else:
                # spanish pron. of e.g. 'bajador'
                if st[pos - 1] in vowels and not is_slavo_germanic \
                        and st[pos + 1] in ['A', 'O']:
                    nxt = ('J', 'H')
                else:
                    if pos == last:
                        nxt = ('J', ' ')
                    else:
                        if st[pos + 1] not in ["L", "T", "K", "S", "N", "M", "B", "Z"] \
                                and st[pos - 1] not in ["S", "K", "L"]:
                            nxt = ('J',)
                        else:
                            nxt = (None,)
            if st[pos + 1] == 'J':
                nxt = nxt + (2,)
            else:
                nxt = nxt + (1,)
        elif ch == 'K':
            if st[pos + 1] == 'K':
                nxt = ('K', 2)
            else:
                nxt = ('K', 1)
        elif ch == 'L':
            if st[pos + 1] == 'L':
                # spanish e.g. 'cabrillo', 'gallegos'
                if (pos == (last - 2) and st[pos - 1:pos + 3] in ["ILLO", "ILLA", "ALLE"]) \
                        or ((st[last - 1:last + 1] in ["AS", "OS"] or st[last] in ["A", "O"]) \
                            and st[pos - 1:pos + 3] == 'ALLE'):
                    nxt = ('L', '', 2)
                else:
                    nxt = ('L', 2)
            else:
                nxt = ('L', 1)
        elif ch == 'M':
            if st[pos + 1:pos + 4] == 'UMB' \
                    and (pos + 1 == last or st[pos + 2:pos + 4] == 'ER') \
                    or st[pos + 1] == 'M':
                nxt = ('M', 2)
            else:
                nxt = ('M', 1)
        elif ch == 'N':
            if st[pos + 1] == 'N':
                nxt = ('N', 2)
            else:
                nxt = ('N', 1)
        elif ch == u'Ñ':
            nxt = ('N', 1)
        elif ch == 'P':
            if st[pos + 1] == 'H':
                nxt = ('F', 2)
            elif st[pos + 1] in ['P', 'B']:  # also account for "campbell", "raspberry"
                nxt = ('P', 2)
            else:
                nxt = ('P', 1)
        elif ch == 'Q':
            if st[pos + 1] == 'Q':
                nxt = ('K', 2)
            else:
                nxt = ('K', 1)
        elif ch == 'R':
            # french e.g. 'rogier', but exclude 'hochmeier'
            if pos == last and not is_slavo_germanic \
                    and st[pos - 2:pos] == 'IE' and st[pos - 4:pos - 2] not in ['ME', 'MA']:
                nxt = ('', 'R')
            else:
                nxt = ('R',)
            if st[pos + 1] == 'R':
                nxt = nxt + (2,)
            else:
                nxt = nxt + (1,)
        elif ch == 'S':
            # special cases 'island', 'isle', 'carlisle', 'carlysle'
            if st[pos - 1:pos + 2] in ['ISL', 'YSL']:
                nxt = (None, 1)
            # special case 'sugar-'
            elif pos == first and st[first:first + 5] == 'SUGAR':
                nxt = ('X', 'S', 1)
            elif st[pos:pos + 2] == 'SH':
                # germanic
                if st[pos + 1:pos + 5] in ["HEIM", "HOEK", "HOLM", "HOLZ"]:
                    nxt = ('S', 2)
                else:
                    nxt = ('X', 2)
            # italian & armenian
            elif st[pos:pos + 3] in ["SIO", "SIA"] or st[pos:pos + 4] == 'SIAN':
                if not is_slavo_germanic:
                    nxt = ('S', 'X', 3)
                else:
                    nxt = ('S', 3)
            # german & anglicisations, e.g. 'smith' match 'schmidt', 'snider' match 'schneider'
            # also, -sz- in slavic language altho in hungarian it is pronounced 's'
            elif (pos == first and st[pos + 1] in ["M", "N", "L", "W"]) or st[pos + 1] == 'Z':
                nxt = ('S', 'X')
                if st[pos + 1] == 'Z':
                    nxt = nxt + (2,)
                else:
                    nxt = nxt + (1,)
            elif st[pos:pos + 2] == 'SC':
                # Schlesinger's rule
                if st[pos + 2] == 'H':
                    # dutch origin, e.g. 'school', 'schooner'
                    if st[pos + 3:pos + 5] in ["OO", "ER", "EN", "UY", "ED", "EM"]:
                        # 'schermerhorn', 'schenker'
                        if st[pos + 3:pos + 5] in ['ER', 'EN']:
                            nxt = ('X', 'SK', 3)
                        else:
                            nxt = ('SK', 3)
                    else:
                        if pos == first and st[first + 3] not in vowels and st[first + 3] != 'W':
                            nxt = ('X', 'S', 3)
                        else:
                            nxt = ('X', 3)
                elif st[pos + 2] in ['I', 'E', 'Y']:
                    nxt = ('S', 3)
                else:
                    nxt = ('SK', 3)
            # french e.g. 'resnais', 'artois'
            elif pos == last and st[pos - 2:pos] in ['AI', 'OI']:
                nxt = ('', 'S', 1)
            else:
                nxt = ('S',)
                if st[pos + 1] in ['S', 'Z']:
                    nxt = nxt + (2,)
                else:
                    nxt = nxt + (1,)
        elif ch == 'T':
            if st[pos:pos + 4] == 'TION':
                nxt = ('X', 3)
            elif st[pos:pos + 3] in ['TIA', 'TCH']:
                nxt = ('X', 3)
            elif st[pos:pos + 2] == 'TH' or st[pos:pos + 3] == 'TTH':
                # special case 'thomas', 'thames' or germanic
                if st[pos + 2:pos + 4] in ['OM', 'AM'] or st[first:first + 4] in ['VON ', 'VAN '] \
                        or st[first:first + 3] == 'SCH':
                    nxt = ('T', 2)
                else:
                    nxt = ('0', 'T', 2)
            elif st[pos + 1] in ['T', 'D']:
                nxt = ('T', 2)
            else:
                nxt = ('T', 1)
        elif ch == 'V':
            if st[pos + 1] == 'V':
                nxt = ('F', 2)
            else:
                nxt = ('F', 1)
        elif ch == 'W':
            # can also be in middle of word
            if st[pos:pos + 2] == 'WR':
                nxt = ('R', 2)
            elif pos == first and (st[pos + 1] in vowels or st[pos:pos + 2] == 'WH'):
                # Wasserman should match Vasserman
                if st[pos + 1] in vowels:
                    nxt = ('A', 'F', 1)
                else:
                    nxt = ('A', 1)
            # Arnow should match Arnoff
            elif (pos == last and st[pos - 1] in vowels) \
                    or st[pos - 1:pos + 5] in ["EWSKI", "EWSKY", "OWSKI", "OWSKY"] \
                    or st[first:first + 3] == 'SCH':
                nxt = ('', 'F', 1)
            # polish e.g. 'filipowicz'
            elif st[pos:pos + 4] in ["WICZ", "WITZ"]:
                nxt = ('TS', 'FX', 4)
            else:  # default is to skip it
                nxt = (None, 1)
        elif ch == 'X':
            # french e.g. breaux
            nxt = (None,)
            if not (pos == last and (st[pos - 3:pos] in ["IAU", "EAU"] \
                                     or st[pos - 2:pos] in ['AU', 'OU'])):
                nxt = ('KS',)
            if st[pos + 1] in ['C', 'X']:
                nxt = nxt + (2,)
            else:
                nxt = nxt + (1,)
        elif ch == 'Z':
            # chinese pinyin e.g. 'zhao'
            if st[pos + 1] == 'H':
                nxt = ('J',)
            elif st[pos + 1:pos + 3] in ["ZO", "ZI", "ZA"] \
                    or (is_slavo_germanic and pos > first and st[pos - 1] != 'T'):
                nxt = ('S', 'TS')
            else:
                nxt = ('S',)
            if st[pos + 1] == 'Z':
                nxt = nxt + (2,)
            else:
                nxt = nxt + (1,)
        # ----------------------------------
        # --- end checking letters------
        # ----------------------------------
        # print str(nxt)
        if len(nxt) == 2:
            if nxt[0]:
                pri += nxt[0]
                sec += nxt[0]
            pos += nxt[1]
        elif len(nxt) == 3:
            if nxt[0]:
                pri += nxt[0]
            if nxt[1]:
                sec += nxt[1]
            pos += nxt[2]
    if pri == sec:
        return (pri, None)
    else:
        return (pri, sec)


def report_search(query, gps_lat, gps_lng, execution_time):
    return False
    try:

        start = time.time()
        session_main = Session_main()

        execution_time = round(execution_time, 2)

        query_orig = query
        query = query.strip()
        query_url = query.replace(" ", "%20")

        print('REPORT SEARCH')
        search_info = session_main.query(models.search).filter(
            (models.search.query == query_orig) &
            (models.search.page == 0) &
            (models.search.time > '2019-04-03 18:24:49')
        ).count()
        session_main.close()

        if search_info > 1:

            new_search = False

            msg = MIMEMultipart('alternative')
            msg['Subject'] = '🔎 Repeat Search Term ' + str(query)
            msg['From'] = 'TopSavings API <mailer@TopSavings.com>'
            msg['To'] = 'TopSavings Team'

            text_gps = 'A TopSavings user searched for ' + query + ' from https://www.google.com/maps/place/' + str(
                gps_lat) + ',' + str(gps_lng) + ' in ' + str(
                execution_time) + ' seconds. \r\n Click https://cms.topsavings.com/cms_products?search=' + query_url + ' to view in CMS'

            text_no_gps = 'A TopSavings user searched for ' + query + ' in ' + str(
                execution_time) + ' seconds. \r\n Click https://cms.topsavings.com/cms_products?search=' + query_url + ' to view in CMS'
        else:
            new_search = True

            msg = MIMEMultipart('alternative')
            msg['Subject'] = '❇️🔎 New Search Term ' + str(query)
            msg['From'] = 'TopSavings API <mailer@TopSavings.com>'
            msg['To'] = 'TopSavings Team'

            text_gps = 'A TopSavings user searched for ' + query + ' for the first time ever from https://www.google.com/maps/place/' + str(
                gps_lat) + ',' + str(gps_lng) + ' in ' + str(
                execution_time) + ' seconds. \r\n Click https://cms.topsavings.com/cms_products?search=' + query_url + ' to view in CMS'
            text_no_gps = 'A TopSavings user searched for ' + query + ' for the first time ever in ' + str(
                execution_time) + ' seconds. \r\n Click https://cms.topsavings.com/cms_products?search=' + query_url + ' to view in CMS'

        part1 = MIMEText(text_gps, 'plain')
        msg.attach(part1)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.ehlo()
        server.starttls()
        server.login(SMTP_LOGIN, SMTP_PASSWORD)

        server.sendmail("mailer@TopSavings.com", "adam@topsavings.com", msg.as_string())
        server.sendmail("mailer@TopSavings.com", "steve@topsavings.com", msg.as_string())
        server.quit()

        part1 = MIMEText(text_no_gps, 'plain')
        msg.attach(part1)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls()
        server.login("mailer@linkclicks.com", SMTP_PASSWORD)

        server.sendmail("mailer@TopSavings.com", "cavemankevo13@gmail.com", msg.as_string())

        server.quit()
        return False

    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        error_message = str(e) + ' ' + str(fname) + ' ' + str(exc_tb.tb_lineno)
        email_crash_report('report_search', error_message)
        return False