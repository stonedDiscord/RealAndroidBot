import sys
from pathlib import Path
import time
import logging
import json
from contextlib import contextmanager
from sqlalchemy import create_engine, Column, Integer, String, Float, SmallInteger, \
    BigInteger, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.types import TypeDecorator, Numeric, Text, DATETIME
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import or_
import logging
from Webhook import get_server_time

import sanitized as config

logger = logging.getLogger('rab')

rab_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(rab_dir))


class DBCacheFortIdsWithinRange:

    def __init__(self, range, lat, lon, ids):
        self.range = range
        self.lat = lat
        self.lon = lon
        self.ids = ids


class DBCache:
    fort_ids_within_range = []
    unknown_fort_id = None
    not_a_fort_id = None


if config.DB_ENGINE.startswith('mysql'):
    from sqlalchemy.dialects.mysql import TINYINT, BIGINT, DOUBLE, LONGTEXT

    TINY_TYPE = TINYINT(unsigned=True)          # 0 to 255
    MEDIUM_TYPE = Integer                       # 0 to 4294967295
    UNSIGNED_HUGE_TYPE = BIGINT(unsigned=True)  # 0 to 18446744073709551615
    HUGE_TYPE = BigInteger
    PRIMARY_HUGE_TYPE = HUGE_TYPE
    FLOAT_TYPE = DOUBLE(precision=18, scale=14, asdecimal=False)
    LONG_TEXT = LONGTEXT
elif config.DB_ENGINE.startswith('postgres'):
    from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION, TEXT

    class NumInt(TypeDecorator):
        '''Modify Numeric type for integers'''
        impl = Numeric

        def process_bind_param(self, value, dialect):
            if value is None:
                return None
            return int(value)

        def process_result_value(self, value, dialect):
            if value is None:
                return None
            return int(value)

        @property
        def python_type(self):
            return int

    TINY_TYPE = SmallInteger                    # -32768 to 32767
    MEDIUM_TYPE = Integer                       # -2147483648 to 2147483647
    UNSIGNED_HUGE_TYPE = NumInt(precision=20, scale=0)   # up to 20 digits
    HUGE_TYPE = BigInteger
    PRIMARY_HUGE_TYPE = HUGE_TYPE
    FLOAT_TYPE = DOUBLE_PRECISION(asdecimal=False)
    LONG_TEXT = TEXT
else:
    class TextInt(TypeDecorator):
        '''Modify Text type for integers'''
        impl = Text

        def process_bind_param(self, value, dialect):
            return str(value)

        def process_result_value(self, value, dialect):
            return int(value)

    TINY_TYPE = SmallInteger
    MEDIUM_TYPE = Integer
    UNSIGNED_HUGE_TYPE = TextInt
    HUGE_TYPE = Integer
    PRIMARY_HUGE_TYPE = HUGE_TYPE
    FLOAT_TYPE = Float(asdecimal=False)

Base = declarative_base()

engine = create_engine(config.DB_ENGINE, pool_size=config.DB_POOL_SIZE,
                       max_overflow=config.DB_MAX_OVERFLOW, pool_recycle=config.DB_POOL_RECYCLE, pool_pre_ping=True)
engine2 = create_engine(config.DB_ENGINE2, pool_size=config.DB_POOL_SIZE,
                        max_overflow=config.DB_MAX_OVERFLOW, pool_recycle=config.DB_POOL_RECYCLE, pool_pre_ping=True)


class Subscriptions(Base):
    __tablename__ = 'subscriptions'

    telegram_id = Column(MEDIUM_TYPE, primary_key=True)
    device_log = Column(String(256))
    donor_tier = Column(String(45))
    donor_until = Column(MEDIUM_TYPE)
    updated = Column(DATETIME)


class DeviceLog(Base):
    __tablename__ = 'device_log'

    id = Column(MEDIUM_TYPE, primary_key=True)
    device_id = Column(String(45))
    client = Column(String(45))
    first_login = Column(MEDIUM_TYPE)
    last_login = Column(MEDIUM_TYPE)


class Forts(Base):
    __tablename__ = 'forts'

    id = Column(MEDIUM_TYPE, primary_key=True)
    external_id = Column(String(35))
    lat = Column(FLOAT_TYPE)
    lon = Column(FLOAT_TYPE)
    name = Column(String(128))
    url = Column(String(200))
    sponsor = Column(TINY_TYPE)
    weather_cell_id = Column(PRIMARY_HUGE_TYPE)
    parkid = Column(MEDIUM_TYPE)
    park = Column(String(200))
    s2cell_lvl12 = Column(String(15))
    s2cell_lvl13 = Column(String(45))
    s2cell_lvl14 = Column(String(45))
    edited_by = Column(String(200))
    submitted_by = Column(String(200))


class Pokestops(Base):
    __tablename__ = 'pokestops'

    id = Column(MEDIUM_TYPE, primary_key=True)
    external_id = Column(String(35))
    lat = Column(FLOAT_TYPE)
    lon = Column(FLOAT_TYPE)
    name = Column(String(128))
    url = Column(String(200))
    updated = Column(MEDIUM_TYPE)
    is_ar_mapping = Column(TINY_TYPE)
    sponsor = Column(TINY_TYPE)
    deployer = Column(String(400))
    lure_start = Column(String(40))
    expires = Column(MEDIUM_TYPE)
    quest = Column(String(256))
    reward = Column(String(128))
    encounter = Column(String(128))
    active_fort_modifier = Column(MEDIUM_TYPE)
    lure_expiration = Column(MEDIUM_TYPE)
    upvote = Column(MEDIUM_TYPE)
    downvote = Column(MEDIUM_TYPE)
    submitter_id = Column(HUGE_TYPE)
    quest_updated = Column(MEDIUM_TYPE)
    incident_character = Column(MEDIUM_TYPE)
    incident_expiration = Column(MEDIUM_TYPE)
    incident_character2 = Column(MEDIUM_TYPE)
    incident_expiration2 = Column(MEDIUM_TYPE)
    incident_verified = Column(MEDIUM_TYPE)
    quest_submitted_by = Column(String(200))
    edited_by = Column(String(200))
    quest_type = Column(TINY_TYPE)
    quest_timestamp = Column(MEDIUM_TYPE)
    quest_target = Column(TINY_TYPE)
    quest_conditions = Column(LONG_TEXT)
    quest_rewards = Column(LONG_TEXT)
    quest_pokemon_id = Column(TINY_TYPE)
    quest_reward_type = Column(TINY_TYPE)
    quest_item_id = Column(TINY_TYPE)


Session = sessionmaker(bind=engine)
Session2 = sessionmaker(bind=engine2)


@contextmanager
def session_scope(autoflush=False):
    """Provide a transactional scope around a series of operations."""
    session = Session(autoflush=autoflush)
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def session2_scope(autoflush=False):
    """Provide a transactional scope around a series of operations."""
    session = Session2(autoflush=autoflush)
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


def get_empty_forts(session):
    try:
        fort_details = session.query(Forts).filter(or_(Forts.name == 'UNKOWN', Forts.name == None,
                                                       Forts.name == '', Forts.url == 'UNKOWN', Forts.url == None, Forts.url == '')).all()
        #fort_details = session.query(Forts).filter_by(name='UNKOWN').all()
    except Exception as e:
        logger.info("Get empty fort error: {}".format(e))
        return False

    return fort_details


def get_empty_pokestops(session):
    try:
        pokestop_details = session.query(Pokestops).with_entities(Pokestops.id, Pokestops.external_id, Pokestops.lat, Pokestops.lon, Pokestops.name, Pokestops.url).filter(
            or_(Pokestops.name == 'UNKOWN', Pokestops.name == None, Pokestops.name == '', Pokestops.url == 'UNKOWN', Pokestops.url == None, Pokestops.url == '')).all()
        #fort_details = session.query(Forts).filter(or_(Forts.name=='UNKOWN',Forts.name==None)).all()
        #fort_details = session.query(Forts).filter_by(name='UNKOWN').all()
    except Exception as e:
        logger.info("Get empty pokestops error: {}".format(e))
        return False

    return pokestop_details


def update_pokestops(session, pokestop_id, pokestop_name, pokestop_url):
    try:
        result = session.query(Pokestops).filter_by(id=pokestop_id).update({
            'name': pokestop_name,
            'url': pokestop_url
        })
    except Exception as e:
        logger.info("Update pokestop error: {}".format(e))
        return False

    return True


def update_forts(session, fort_id, fort_name, fort_url):
    try:
        result = session.query(Forts).filter_by(id=fort_id).update({
            'name': fort_name,
            'url': fort_url
        })
    except Exception as e:
        logger.info("Update fort error: {}".format(e))
        return False

    return True


def device_checkin(session, device_id, client):
    last_login = 0
    device = session.query(DeviceLog).filter_by(device_id=device_id).first()
    server_time = get_server_time()
    if not server_time:
        server_time = int(time.time())
    if device is None:
        session.add(DeviceLog(device_id=device_id, client=client, first_login=server_time, last_login=server_time))
        session.commit()
        return 0
        #device = session.query(DeviceLog).filter_by(device_id=device_id).first()
        #device.last_login = 0
    else:
        last_login = device.last_login
        first_login = device.first_login
        if not first_login or first_login == 'NULL':
            device = session.query(DeviceLog).filter_by(device_id=device_id).update({
                'first_login': server_time,
                'last_login': server_time
            })
            first_login = server_time
        else:
            # Prevent back tracking of system time
            if server_time > device.last_login:
                device = session.query(DeviceLog).filter_by(device_id=device_id).update({
                    'last_login': server_time
                })
            session.commit()

    return first_login, last_login


def vaild_subscription(session, telegram_id):
    server_time = get_server_time()
    if not server_time:
        server_time = int(time.time())
    subscription_details = session.query(Subscriptions).filter_by(telegram_id=telegram_id).first()
    if subscription_details:
        current_time = server_time
        if current_time <= subscription_details.donor_until:
            return subscription_details.donor_until
        else:
            return -1

    return False


def donation_status(session, telegram_id, device_id=None):
    server_time = get_server_time()
    if not server_time:
        server_time = int(time.time())

    device_list = None
    subscription_details = session.query(Subscriptions).filter_by(telegram_id=telegram_id).first()
    if subscription_details:
        current_time = server_time
        #print('debug: current: {} donor until {}'.format(current_time, subscription_details.donor_until))
        if current_time <= subscription_details.donor_until:
            if not subscription_details.device_log:
                device_list = []
            else:
                device_list = json.loads(subscription_details.device_log)
            #print('debug: device list: {}'.format(device_list))
            if len(device_list):
                if len(device_list) < 3 and device_id.lower() not in device_list:
                    device_list.append(device_id.lower())
                    session.query(Subscriptions).filter_by(telegram_id=telegram_id).update({
                        'device_log': json.dumps(device_list)
                    })
                    return len(device_list)  # Vaild Device
                elif len(device_list) <= 3 and device_id in device_list:
                    return len(device_list)  # Vaild Device
                else:
                    # More than 3 and not in device list
                    return len(device_list)
            else:
                device_list.append(device_id.lower())
                session.query(Subscriptions).filter_by(telegram_id=telegram_id).update({
                    'device_log': json.dumps(device_list)
                })
                return len(device_list)  # Vaild Device
        else:
            return -1

    return 0

    # update example
    # if FORT_CACHE.gyms[external_id]['weather_cell_id'] is None and raw_fort.get('weather_cell_id'):
    #    session.query(Fort) \
    #        .filter(Fort.id == internal_id) \
    # .update({
    #            'weather_cell_id': raw_fort.get('weather_cell_id')
    #        })

    # delete exmaple
    # spawnpoint = session.query(Spawnpoint) \
    #    .filter(Spawnpoint.spawn_id == spawn_id) \
    #    .first()
    # session.delete(spawnpoint)
    # session.commit()

    # or
    # session.query(GymDefender).filter(GymDefender.fort_id==fort_internal_id).delete()
