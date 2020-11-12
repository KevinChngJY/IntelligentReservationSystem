import re
import json
import sqlite3
import numpy as np
import pandas as pd

from ira import Agent
from tqdm import tqdm
from time import sleep
from faker import Faker
from random import randint, randrange, shuffle
from datetime import datetime, timedelta, time, date


ts_dt_str = '%y/%m/%d_%H:%M:%S.%f'


def create_dummy_db(sources, target):
    # dummy db
    conn = sqlite3.connect(target)
    curs = conn.cursor()
    for source in sources:
        tn = source.split('.')[0]
        curs.execute(f"DROP TABLE IF EXISTS {tn}")
        df = pd.read_csv(source)
        df['id'] = df.index.tolist()
        df.to_sql(tn, con=conn)
    conn.commit()
    conn.close()
    del conn
    return

def create_dummy_persons(n, target=None):
    f = Faker()
    persons = []
    for _ in range(n):
        ts = datetime.strftime(datetime.now(), ts_dt_str)
        name = f.name()
        dob = f.date_of_birth()
        username = name.lower().replace(' ', '') + dob.strftime('%y%m%d')
        password = f.pystr(min_chars=8, max_chars=12)
        email = name.lower().replace(' ', '.') + '@test.com.sg'
        phone = randint(80000000, 99999999)
        persons.append([name, dob.strftime('%y/%m/%d'), username, password, email, phone])
    persons = pd.DataFrame(persons, 
                           columns=['name', 'dob', 'username', 'password', 'email', 'phone'])
    persons['id'] = persons.index
    if target:
        persons.to_csv(target, index=False)
    return persons

def create_dummy_businesses(n, target=None):
    f = Faker()
    businesses = []
    for _ in range(n):
        ts = datetime.strftime(datetime.now(), ts_dt_str)
        name = f"{f.company()}"
        username = re.sub(r'\W+', '', name).lower() + str(randint(1000, 9999))
        password = f.pystr(min_chars=8, max_chars=12)
        email = username + '@test.com.sg'
        phone = randint(60000000, 69999999)
        if randint(0, 2):
            sublocs = [randint(1, 10) for _ in range(randint(1, 20))]
            sublocs = dict(zip([f"S{i}" for i in range(len(sublocs))], sublocs))
            max_cap = sum([int(i) for i in sublocs.values()])
            sublocs = json.dumps(sublocs).replace(' ', '')
        else:
            max_cap = randint(20, 101)
            sublocs = '-'
        open_days = ''.join([str(i) for i in range(1, randint(6, 8))])
        open_time = time(randint(6, 12), randrange(0, 60, 30), 0).strftime('%H%M')
        close_time = time(randint(14, 23), randrange(0, 60, 30), 0).strftime('%H%M')
        default_duration = randrange(10, 30, 10)
        max_group_size = 5
        days_in_advance = randint(1, 2)
        businesses.append([ts, name, username, password, email, phone, 
                           sublocs, max_cap, open_days, open_time, close_time, 
                           max_group_size, default_duration, days_in_advance])
    businesses = pd.DataFrame(businesses, 
                              columns=['timestamp', 'name', 'username', 'password', 'email', 'phone', 
                                       'sublocs', 'max_cap', 'open_days', 'open_time', 'close_time', 
                                       'max_group_size', 'default_duration', 'days_in_advance'])
    businesses['id'] = businesses.index
    if target is not None:
        businesses.to_csv(target, index=False)
    return businesses

def create_dummy_appointments(n_day=3, db='dummy.db', tn_pat='dummy_pat', tn_est='dummy_est'):
    # simulation
    randomizer1, randomizer2 = 2, 10
    intent = 'NewReservation'
    patrons = load_table(tn_pat, db=db)
    settings = load_table(tn_est, db=db)
    for n in range(n_day):
        print(f"Day #{n}")
        sleep(1)
        for business in settings['username'].drop_duplicates():
            try:
                setting = settings.loc[settings['username'] == business].sort_values('timestamp', ascending=False).iloc[0]
            except KeyError:
                setting = settings.loc[settings['username'] == business].sort_values('id', ascending=False).iloc[0]
            days_in_advance, duration, max_cap = int(setting['days_in_advance']), int(setting['default_duration']), int(setting['max_cap'])
            opening, closing = setting['open_time'], setting['close_time']
            opening, closing = datetime.strptime(opening, '%H%M'), datetime.strptime(closing, '%H%M')
            n_slot = (closing - opening).seconds // (duration * 60)
            now = datetime.now()
            start = datetime(year=now.year, month=now.month, day=now.day+days_in_advance+np.random.randint(-1, 1), 
                            hour=opening.hour, minute=opening.minute, second=0) + timedelta(days=n)
            parallel = round(max_cap / 5)
            if parallel == 0:
                parallel = 1
            ctr, n_reservation = 0, np.random.randint(parallel * n_slot, parallel * n_slot * randomizer1)
            for _ in tqdm(range(n_reservation)):
                a, b = np.random.randint(0, n_slot), np.random.randint(1, 5)
                if a + b > n_slot:
                    continue
                a = start + timedelta(seconds=(duration-np.random.randint(randomizer2))*60*a)
                b = a + timedelta(seconds=(duration+np.random.randint(randomizer2))*60*b)
                patron = patrons.loc[np.random.randint(0, patrons.shape[0]), 'username']
                a, b = datetime.strftime(a, '%y/%m/%d_%H:%M'), datetime.strftime(b, '%y/%m/%d_%H:%M')
                ts = str(int(datetime.now().timestamp()*1e6))
                response = Agent(ts, intent, patron, business, time_in=a, time_out=b, n_person=str(np.random.randint(1, randomizer2))).check_rules()
                sleep(0.00001)
                if response[0] == '1':
                    continue
                # print(response)
                # f"Time frame that fits your preferences is {start} to {end}. Please confirm if it's okay for you"
                # f"Available time slot(s): \n(1) Thursday 29 October 2020 at 07:00\n(2) Thursday 29 October 2020 at 08:30"
                if 'Available time slot(s): \n' in response[1]:
                    offer = datetime.strptime(response[1].split('\n')[1][4:], '%A %d %B %Y at %H:%M')
                    offer = datetime.strftime(offer, '%y/%m/%d_%H:%M')
                elif 'Time frame that fits your preferences is ' in response[1]:
                    offer = response[1].replace('Time frame that fits your preferences is ', '').split(' to ')[0]
                    offer = datetime.strptime(offer, '%A %d %B %Y at %H:%M')
                    offer = datetime.strftime(offer, '%y/%m/%d_%H:%M')
                else:
                    continue
                # print(offer)
                response = Agent(ts, intent, patron, business, selection=offer).check_rules()
                sleep(0.00001)
                # print(response)
                if response[0] == '-1':
                    ctr += 1

def load_table(tn, db='dummy.db'):
    conn = sqlite3.connect(db)
    df = pd.read_sql(f"SELECT * FROM {tn}", conn)
    conn.close()
    del conn
    return df

def df_to_table(df, tn, db='dummy.db'):
    conn = sqlite3.connect(db)
    df.to_sql(tn, conn, index=False)
    conn.commit()
    conn.close()
    del conn
    return

def drop_table(tn, db='dummy.db'):
    conn = sqlite3.connect(db)
    conn.cursor().execute(f"DROP TABLE {tn}")
    conn.commit()
    conn.close()
    del conn
    return

def create_qry_report_table(tn='dummy_qry_report', db='dummy.db'):
    conn = sqlite3.connect(db)
    conn.cursor().execute(f"CREATE TABLE {tn} ({', '.join(['id INTEGER PRIMARY KEY', 'establishment', 'timestamp', 'period', 'n_total'])})")
    conn.commit()
    conn.close()
    del conn
    return

def init_db(db='dummy.db', 
            tn_pat='dummy_pat', tn_est='dummy_est', 
            tn_qry='dummy_qry', tn_rsv='dummy_rsv', 
            tn_qry_report='dummy_qry_report', tn_rsv_report='dummy_rsv_report', 
            n_establishment=5, n_patron=100):

    conn = sqlite3.connect(db)
    cursor = conn.cursor()

    qry = (tn_qry, ['id INTEGER PRIMARY KEY', 'session', 'timestamp', 'patron', 'establishment', 'n_person', 'time_in', 'time_out', 'intent', 'step', 'action', 'selection'])
    rsv = (tn_rsv, ['id INTEGER PRIMARY KEY', 'session', 'timestamp', 'patron', 'establishment', 'n_person', 'time_in', 'time_out', 'intent', 'status', 'loc'])
    qry_report = (tn_qry_report, ['id INTEGER PRIMARY KEY', 'establishment', 'timestamp', 'period', 'n_total'])
    rsv_report = (tn_rsv_report, ['id INTEGER PRIMARY KEY', 'timestamp', 'establishment', 'hourly', 'utilization', 'acceptance', 'source', 'period'])
    for tn, clm in [qry, rsv, qry_report, rsv_report]:
        cursor.execute(f"CREATE TABLE {tn} ({', '.join(clm)})")

    df_to_table(create_dummy_persons(n_patron), tn_pat, db)
    df_to_table(create_dummy_businesses(n_establishment), tn_est, db)
    
    conn.commit()
    conn.close()
    del cursor, conn

    return
