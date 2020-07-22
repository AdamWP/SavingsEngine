from sqlalchemy import Column, Integer, String, DateTime, Numeric, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


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


class magic_tokens(Base):
    __tablename__ = 'magic_tokens'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(36))
    magic = Column(String(400))
    expiry = Column(DateTime)
    ipaddress = Column(Integer)
    redeemed_on = Column(DateTime)
    redeemed_ipaddress = Column(Integer)