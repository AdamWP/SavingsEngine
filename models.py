from sqlalchemy import Column, Integer, String, DateTime, Numeric, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class api_activity(Base):
    __tablename__ = 'api_activity'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    date_time = Column(DateTime)
    gps_lat = Column(Numeric)
    gps_lng = Column(Numeric)
    OS = Column(Text)
    endpoint = Column(String(200))


class user(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True)
    password = Column(Text)
    password_new = Column(Text)
    email = Column(String(200))
    first_name = Column(String(45))
    last_name = Column(String(45))
    name = Column(String(100))
    fb_id = Column(String(45))
    fb_picture = Column(String(200))
    join_date = Column(DateTime)
    distance = Column(Numeric)
    range = Column(Text)
    units = Column(Text)
    gps_lat = Column(Numeric)
    gps_lng = Column(Numeric)
    zip = Column(Text)
    points = Column(Integer)
    savings = Column(Numeric)
    demo = Column(Integer)
    dev = Column(Integer)
    training = Column(Integer)
    admin = Column(Integer)
    device = Column(Text)
    location_services = Column(Text)
    OS = Column(Text)
    app_version = Column(Text)
    last_session_start = Column(DateTime)
    last_here = Column(DateTime)
    share_code = Column(Text)
    fcm_token = Column(String(255))
    email_unsub_key = Column(String(36))
    confirmation_key = Column(String(36))
    zone_id = Column(Integer)


class user_mem(Base):
    __tablename__ = 'user_mem'

    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True)
    password = Column(Text)
    password_new = Column(Text)
    email = Column(String(500))
    first_name = Column(String(45))
    last_name = Column(String(45))
    name = Column(String(100))
    fb_id = Column(String(45))
    distance = Column(Numeric)
    units = Column(Text)
    zip = Column(Text)
    points = Column(Integer)
    demo = Column(Integer)
    training = Column(Integer)
    admin = Column(Integer)
    device = Column(Text)
    location_services = Column(Text)
    OS = Column(Text)
    app_version = Column(Text)
    last_session_start = Column(DateTime)
    last_here = Column(DateTime)
    share_code = Column(Text)
    fcm_token = Column(String(255))


class user_fcm(Base):
    __tablename__ = 'user_fcm'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    fcm_token = Column(String(255))
    date_time = Column(DateTime)
    date_time_disabled = Column(DateTime)
    OS = Column(Text)


class user_savings(Base):
    __tablename__ = 'user_savings'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    prod_id = Column(String(36))
    scan_id = Column(Integer)
    savings = Column(Numeric)
    savings_type = Column(Text)
    post_time = Column(DateTime)


class user_settings(Base):
    __tablename__ = 'user_settings'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    name = Column(Text)
    enabled_time = Column(DateTime)
    disabled_time = Column(DateTime)


class user_stores_disabled(Base):
    __tablename__ = 'user_stores_disabled'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    store_id = Column(Integer)
    chain = Column(Text)
    disabled_time = Column(DateTime)
    enabled_time = Column(DateTime)


class item_info(Base):
    __tablename__ = 'item_info'

    id = Column(Integer, primary_key=True)
    prod_id = Column(String(36))
    brand = Column(Text)
    prod_name = Column(Text)
    size = Column(Text)
    units = Column(Text)
    sub_category2 = Column(Text)
    awaiting_approval = Column(Integer)


class item_info_mem(Base):
    __tablename__ = 'item_info_mem'

    id = Column(Integer, primary_key=True)
    prod_id = Column(String(36))
    brand = Column(Text)
    prod_name = Column(Text)
    size = Column(Text)
    units = Column(Text)
    category = Column(Text)
    sub_category1 = Column(Text)
    sub_category2 = Column(Text)
    sub_category3 = Column(Text)
    sub_category4 = Column(Text)
    calories = Column(Text)
    description = Column(Text)
    nutr_grade = Column(Text)
    auto_submitted_on = Column(DateTime)
    auto_submitted_by = Column(Integer)
    awaiting_approval = Column(Integer)
    ipaddress = Column(Text)
    disabled = Column(Integer)
    disabled_by = Column(Integer)
    disabled_datetime = Column(DateTime)
    submitted_scan_id = Column(Integer)


class item_info_unknown(Base):
    __tablename__ = 'item_info_unknown'

    id = Column(Integer, primary_key=True)
    scan_id = Column(Integer)
    barcode = Column(Text)
    item_text = Column(String(600))
    submitted_on = Column(DateTime)
    submitted_by = Column(Text)
    ipaddress = Column(Text)
    disabled = Column(Integer)
    suggested_search = Column(Text)


class item_info_unknown_images(Base):
    __tablename__ = 'item_info_unknown_images'

    id = Column(Integer, primary_key=True)
    scan_id = Column(Integer)
    image = Column(Text)
    suggested_search = Column(Text)
    rating_key = Column(String(36))
    submitted_on = Column(DateTime)
    submitted_by = Column(Text)
    ipaddress = Column(Text)


class product_codes(Base):
    __tablename__ = 'product_codes'

    id = Column(Integer, primary_key=True)
    prod_id = Column(String(36))
    code = Column(Text)
    type = Column(Text)
    chain = Column(Text)
    disabled = Column(Integer)
    disabled_by = Column(Integer)
    disabled_datetime = Column(DateTime)
    added_by = Column(Integer)
    added_datetime = Column(DateTime)


class product_codes_mem(Base):
    __tablename__ = 'product_codes_mem'

    id = Column(Integer, primary_key=True)
    prod_id = Column(String(36))
    code = Column(Text)
    type = Column(Text)
    chain = Column(Text)
    disabled = Column(Integer)
    disabled_by = Column(Integer)
    disabled_datetime = Column(DateTime)
    added_by = Column(Integer)
    added_datetime = Column(DateTime)


class urls(Base):
    __tablename__ = 'urls'

    id = Column(Integer, primary_key=True)
    prod_id = Column(String(36))
    url = Column(Text)
    chain = Column(Text)
    disabled = Column(Integer)
    disabled_by = Column(Integer)
    added_by  = Column(Integer)
    added_datetime = Column(DateTime)


class urls_mem(Base):
    __tablename__ = 'urls_mem'

    id = Column(Integer, primary_key=True)
    prod_id = Column(String(36))
    url = Column(Text)
    chain = Column(Text)
    added_by  = Column(Integer)
    added_datetime = Column(DateTime)


class url_clicks(Base):
    __tablename__ = 'url_clicks'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    urls_id = Column(Integer)
    date_time = Column(DateTime)


class images(Base):
    __tablename__ = 'images'

    id = Column(Integer, primary_key=True)
    prod_id = Column(String(36))
    image_url = Column(Text)
    image = Column(Text)
    disabled = Column(Integer)


class images_mem(Base):
    __tablename__ = 'images_mem'

    id = Column(Integer, primary_key=True)
    prod_id = Column(String(36))
    image = Column(Text)


class magic_tokens(Base):
    __tablename__ = 'magic_tokens'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(36))
    magic = Column(String(400))
    expiry = Column(DateTime)
    ipaddress = Column(Integer)
    redeemed_on = Column(DateTime)
    redeemed_ipaddress = Column(Integer)


class Submission(Base):
    __tablename__ = 'submission'

    id = Column(Integer, primary_key=True)
    scan_id = Column(Integer)
    prod_id = Column(String(36))
    post_time = Column(DateTime)
    item_text = Column(Text)
    barcode = Column(Text)
    scanned_price = Column(Text)
    quantity = Column(Numeric)
    currency = Column(Text)
    price = Column(Text)
    unit_price = Column(Text)
    units = Column(Text)
    store_id = Column(Integer)
    expired = Column(Integer)


class price_reports(Base):
    __tablename__ = 'price_reports'

    id = Column(Integer, primary_key=True)
    prod_id = Column(String(36))
    user_id = Column(Text)
    gps_lat = Column(Numeric)
    gps_lng = Column(Numeric)
    store_id = Column(Integer)
    quantity = Column(Numeric)
    currency = Column(Text)
    price = Column(Text)
    post_time = Column(DateTime)
    ipaddress = Column(Text)


class scans(Base):
    __tablename__ = 'scans'

    scan_id = Column(Integer, primary_key=True)
    post_time = Column(DateTime)
    start = Column(DateTime)
    expiry = Column(DateTime)
    user_id = Column(Text)
    store_id = Column(Text)
    gps_lat = Column(Numeric)
    gps_lng = Column(Numeric)
    scanned_barcode = Column(Text)
    barcode_accuracy = Column(Text)
    scanned_text = Column(String(600))
    text_accuracy = Column(Text)
    quantity = Column(Numeric)
    currency = Column(Text)
    estimated_price = Column(Text)
    scanned_price = Column(Text)
    price = Column(Text)
    unit_price = Column(Numeric)
    price_accuracy = Column(Text)
    image = Column(Text)
    prod_id = Column(String(36))
    prod_id_alt = Column(String(36))
    ipaddress = Column(Text)
    note = Column(Text)
    expired = Column(Integer)
    scan_time = Column(Numeric)
    scan_type = Column(Text)
    watson_confirmed = Column(Integer)
    google_confirmed = Column(Integer)
    uuid = Column(String(36))


class scans_mem(Base):
    __tablename__ = 'scans_mem'

    scan_id = Column(Integer, primary_key=True)
    post_time = Column(DateTime)
    start = Column(DateTime)
    expiry = Column(DateTime)
    user_id = Column(Text)
    store_id = Column(Text)
    gps_lat = Column(Numeric)
    gps_lng = Column(Numeric)
    scanned_barcode = Column(Text)
    barcode_accuracy = Column(Text)
    scanned_text = Column(String(600))
    text_accuracy = Column(Text)
    quantity = Column(Numeric)
    currency = Column(Text)
    estimated_price = Column(Text)
    scanned_price = Column(Text)
    price = Column(Text)
    unit_price = Column(Numeric)
    price_accuracy = Column(Text)
    image = Column(Text)
    prod_id = Column(String(36))
    prod_id_alt = Column(String(36))
    ipaddress = Column(Text)
    note = Column(Text)
    expired = Column(Integer)
    scan_time = Column(Numeric)
    scan_type = Column(Text)
    watson_confirmed = Column(Integer)
    google_confirmed = Column(Integer)
    uuid = Column(String(36))


class search(Base):
    __tablename__ = 'search'

    id = Column(Integer, primary_key=True)
    user_id = Column(Text)
    query = Column(Text)
    page = Column(Integer)
    time = Column(DateTime)
    gps_lat = Column(Numeric)
    gps_lng = Column(Numeric)


class search_tags(Base):
    __tablename__ = 'search_tags'

    id = Column(Integer, primary_key=True)
    tag = Column(Text)
    prod_id = Column(String(36))


class categories_tapped(Base):
    __tablename__ = 'categories_tapped'

    id = Column(Integer, primary_key=True)
    user_id = Column(Text)
    query = Column(Text)
    page = Column(Integer)
    time = Column(DateTime)
    gps_lat = Column(Numeric)
    gps_lng = Column(Numeric)


class infoPage_req(Base):
    __tablename__ = 'infoPage_req'

    id = Column(Integer, primary_key=True)
    prod_id = Column(String(36))
    req_time = Column(DateTime)
    user_id = Column(Text)
    gps_lat = Column(Numeric)
    gps_lng = Column(Numeric)


class shopping_list(Base):
    __tablename__ = 'shopping_list'

    id = Column(Integer, primary_key=True)
    prod_id = Column(String(36))
    generic_name = Column(String(36))
    user_id = Column(Text)
    checked = Column(Integer)


class shopping_lists_completed(Base):
    __tablename__ = 'shopping_lists_completed'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    date_time = Column(DateTime)
    list_size = Column(Integer)


class stores(Base):
    __tablename__ = 'stores'

    id = Column(Integer, primary_key=True)
    chain = Column(Text)
    name = Column(Text)
    address = Column(Text)
    address2 = Column(Text)
    city = Column(Text)
    state = Column(Text)
    zip = Column(Text)
    country = Column(Text)
    phone = Column(Text)
    logo = Column(Text)
    gps_lat = Column(Numeric(precision=10, scale=8))
    gps_lng = Column(Numeric(precision=11, scale=8))
    websearch = Column(Integer)

class stores_mem(Base):
    __tablename__ = 'stores_mem'

    id = Column(Integer, primary_key=True)
    chain = Column(Text)
    name = Column(Text)
    address = Column(Text)
    address2 = Column(Text)
    city = Column(Text)
    state = Column(Text)
    zip = Column(Text)
    country = Column(Text)
    phone = Column(Text)
    logo = Column(Text)
    gps_lat = Column(Numeric(precision=10, scale=8))
    gps_lng = Column(Numeric(precision=11, scale=8))
    websearch = Column(Integer)

class stores_cookies(Base):
    __tablename__ = 'stores_cookies'

    id = Column(Integer, primary_key=True)
    store_id = Column(Integer)
    cookie = Column(Text)
    date_time = Column(DateTime)
    loblaws_csrf = Column(String(36))
    loblaws_data_cart_id = Column(Integer)

class website_down_time(Base):
    __tablename__ = 'website_down_time'

    id = Column(Integer, primary_key=True)
    chain = Column(Text)
    down_time = Column(DateTime)
    source = Column(Text)

class wait_list(Base):
    __tablename__ = 'wait_list'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    fav_store = Column(Text)
    gps_lat = Column(Numeric)
    gps_lng = Column(Numeric)
    join_date = Column(DateTime)

class geofence_notifications(Base):
    __tablename__ = 'geofence_notifications'

    id = Column(Integer, primary_key=True)
    notification = Column(Text)
    in_store_deal = Column(Integer)
    expired = Column(Integer)

class geofence_notifications_sent(Base):
    __tablename__ = 'geofence_notifications_sent'

    id = Column(Integer, primary_key=True)
    geofence_notification_id = Column(Integer)
    user_id = Column(Integer)
    store_id = Column(Integer)
    prod_id = Column(String(36))
    price = Column(Numeric)
    savings_price = Column(Numeric)
    sent_time = Column(DateTime)
    opened_time = Column(DateTime)
    gps_lat_sent = Column(Numeric)
    gps_lng_sent = Column(Numeric)
    gps_lat_opened = Column(Numeric)
    gps_lng_opened = Column(Numeric)
    expired = Column(Integer)
    default_notification=Column(Integer)


class notifications(Base):
    __tablename__ = 'notifications'

    id = Column(String(36), primary_key=True)
    date_time = Column(DateTime)
    title = Column(String(45))
    message = Column(String(255))
    prod_id = Column(String(36))
    store_chain = Column(String(45))
    store_id = Column(Integer)
    image_url = Column(String(255))
    user_id = Column(Integer)
    created_on = Column(DateTime)
    sound = Column(String(45))
    notification_type = Column(Text)

class notifications_sent(Base):
    __tablename__ = 'notifications_sent'

    id = Column(String(36), primary_key=True)
    notification_id = Column(String(36))
    user_id = Column(Integer)
    date_time_scheduled = Column(DateTime)
    date_time_sent = Column(DateTime)
    date_time_opened = Column(DateTime)

class points(Base):
    __tablename__ = 'points'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    scan_id = Column(Integer)
    prod_id = Column(String(36))
    token = Column(String(36))
    points = Column(Integer)
    note = Column(Text)
    post_time = Column(DateTime)
    reward_type = Column(Text)
    offered_on = Column(DateTime)
    earned_on = Column(DateTime)
    deals_shared_opened_id = Column(Integer)
    referrals_id = Column(Integer)


class referrals(Base):
    __tablename__ = 'referrals'

    id = Column(Integer, primary_key=True)
    share_code = Column(Text)
    user_id = Column(Integer)
    date_time = Column(DateTime)
    ipaddress = Column(Text)
    note = Column(Text)

class deals(Base):
    __tablename__ = 'deals'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    date_time = Column(DateTime)


class deals_displayed(Base):
    __tablename__ = 'deals_displayed'
    id = Column(Integer, primary_key=True)
    deal_id = Column(String(36))
    prod_id = Column(String(36))
    min_price = Column(Numeric)
    save_price = Column(Numeric)
    user_id = Column(Integer)
    store_id = Column(Integer)
    chain_count = Column(Integer)
    date_time = Column(DateTime)
    gps_lat = Column(Numeric)
    gps_lng = Column(Numeric)

class deals_tapped(Base):
    __tablename__ = 'deals_tapped'
    id = Column(Integer, primary_key=True)
    prod_id = Column(String(36))
    deal_id = Column(String(36))
    user_id = Column(Integer)
    date_time = Column(DateTime)
    gps_lat = Column(Numeric)
    gps_lng = Column(Numeric)
    search_query = Column(Text)
    scan_id = Column(Integer)
    referrer = Column(Text)
    price = Column(Numeric)
    currency = Column(Text)
    saving_price = Column(Numeric)
    store_id = Column(Integer)
    execution_time = Column(Numeric)

class deals_shared_opened(Base):
    __tablename__ = 'deals_shared_opened'
    id = Column(Integer, primary_key=True)
    share_id = Column(String(36))
    ipaddress = Column(Text)
    user_id = Column(Integer)

class categories(Base):
    __tablename__ = 'categories'
    pri = Column(Integer, primary_key=True)
    id = Column(Integer)
    category = Column(String(36))
    image = Column(String(45))

class web_search_threads(Base):
    __tablename__ = 'web_search_threads'
    id = Column(Integer, primary_key=True)
    chain = Column(Text)
    threads = Column(Integer)