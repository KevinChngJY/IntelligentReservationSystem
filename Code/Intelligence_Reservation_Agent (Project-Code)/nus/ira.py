import json
# import pytz
import sqlite3
import numpy as np
import pandas as pd
import random as rd
import configparser
import matplotlib.pyplot as plt

from tqdm import tqdm
from time import sleep
from typing import Union
from random import randint
from functools import reduce
from math import ceil, floor
from types import FunctionType
from operator import itemgetter
from itertools import product, chain
from datetime import datetime, timedelta

ts_dt_str = '%y/%m/%d_%H:%M:%S.%f'
std_dt_str = '%y/%m/%d_%H:%M'
str_to_dt = lambda dt: datetime.strptime(dt, std_dt_str)
dt_to_str = lambda dt: datetime.strftime(dt, std_dt_str)
is_debug_mode = False
default_config_file_path = 'config.ini'


def config_read(config_file=default_config_file_path):
    config = configparser.ConfigParser()
    config.read(config_file)
    return config


def config_read_db(config_file=default_config_file_path):
    config = config_read(config_file)
    db = config['DB']
    return db['path'], db['table_est'], db['table_pat'], db['table_rsv'], db['table_qry'], db['table_rsv_report'], db['table_qry_report']


def config_read_return_dict(section, config_file=default_config_file_path):
    config = config_read(config_file)
    return config[section]


class HouseKeeping:
    # 1. free up on-hold, rsv
    def __init__(self, timeout=60, **kwargs):
        self.timeout = timeout
        self.loader = Loader()
        if 'session' in kwargs:
            self.session = kwargs['session']
            self.timeout_check()
            # self.expiry_check()
        else:
            # self.genetic_algorithm_check()
            self.n_attempt = 3

    def timeout_check(self):
        on_hold = self.loader.load_from_table(self.loader.tn_qry)
        # on_hold = on_hold.loc[~on_hold['session'].str.contains('|')]
        on_hold = on_hold.loc[on_hold['session'].apply(lambda sess: True if '|' not in sess else False)]
        for _, row in on_hold.iterrows():
            if datetime.now() - datetime.strptime(row['timestamp'], ts_dt_str) > timedelta(seconds=self.timeout):
                # session expires
                expired_sess = f"{self.session.split('|')[0]}|{round(datetime.now().timestamp())}|timeout"
                self.loader.update_cell(self.loader.tn_qry, ('session', expired_sess), **row.to_dict())
        return

    def expiry_check(self):
        on_hold = self.loader.load_from_table(self.loader.tn_rsv)
        on_hold.loc[on_hold['time_out'].apply(str_to_dt) < datetime.now(), 'status'] = 'completed'
        return

    # n_generation is hardcoded
    def genetic_algorithm_check(self, n_generation=1000, all_days=False, plot=False):
        on_hold = self.loader.load_from_table(self.loader.tn_rsv)
        on_hold = on_hold.loc[on_hold['status'] == 'on-hold']
        hm_parser = lambda hm: datetime.strptime(hm, '%H%M')
        # for every establishment
        for name, g in on_hold.groupby('establishment'):
            # load establishment setting
            est = self.loader.load_from_table(self.loader.tn_est)
            try:
                est = est.loc[est['username'] == name].sort_values('timestamp', ascending=False).reset_index(drop=True).iloc[0]
            except KeyError:
                est = est.loc[est['username'] == name].sort_values('id', ascending=False).reset_index(drop=True).iloc[0]
            # default duration and max cap
            est_default_duration = int(est['default_duration'])
            est_max_cap = int(est['max_cap'])
            est_days_in_advance = int(est['days_in_advance'])
            # open time
            open_time = hm_parser(est['open_time'])
            n_slot = (hm_parser(est['close_time']) - open_time).seconds // (est_default_duration * 60)
            # prepare for GA, do not mess with the sequence
            now = datetime.now()
            today_midnight = datetime(year=now.year, month=now.month, day=now.day, hour=0, minute=0, second=0)
            # print(today_midnight + timedelta(days=est_days_in_advance+2))
            # print(g['time_in'].apply(str_to_dt))
            if all_days:
                # all business days
                days = g['time_in'].apply(lambda dt: dt.split('_')[0]).drop_duplicates()
                masks = list(map(lambda day: g['time_in'].apply(lambda dt: dt.split('_')[0]) == day, days))
            else:
                # next business day
                ti = g['time_in'].apply(str_to_dt)
                mask = ti < today_midnight + timedelta(days=est_days_in_advance+2)
                mask &= today_midnight + timedelta(days=est_days_in_advance+1) <= ti
                masks = [mask]
            for mask in masks:
                iop = g.loc[mask, ['timestamp', 'time_in', 'time_out', 'n_person']].copy().astype('object').reset_index(drop=True)
                if iop.shape[0] == 0:
                    continue
                # time_in and time_out have day month year
                target_day = str_to_dt(iop['time_in'].iloc[0])
                target_day = datetime(year=target_day.year, month=target_day.month, day=target_day.day, 
                                    hour=open_time.hour, minute=open_time.minute, second=open_time.second)
                iop['time_in'] = iop['time_in'].apply(lambda ymd_hm: hm_parser(ymd_hm.split('_')[1].replace(':', '')))
                iop['time_out'] = iop['time_out'].apply(lambda ymd_hm: hm_parser(ymd_hm.split('_')[1].replace(':', '')))
                open_time = iop['time_in'].apply(lambda ti: datetime(year=ti.year, month=ti.month, day=ti.day, 
                                                                    hour=open_time.hour, minute=open_time.minute, second=open_time.second)).iloc[0]
                start = (iop['time_in'] - open_time).apply(lambda s: s.seconds // (est_default_duration * 60)).tolist()
                n_block = (iop['time_out'] - iop['time_in']).apply(lambda diff: diff.seconds // (est_default_duration * 60)).tolist()
                n_person = iop['n_person'].astype(int).tolist()
                # build allreqs
                allreqs = np.zeros((iop.shape[0], n_slot))
                builder = np.array([start, n_block, n_person]).T
                for i in range(allreqs.shape[0]):
                    s, b, p = builder[i]
                    for j in range(s, s + b):
                        allreqs[i, j] = p
                # for r in allreqs:
                #     print(r)
                if allreqs.shape[0] > 0:
                    # run GA
                    for i in range(1, self.n_attempt + 1):
                        print(f"{name} {target_day} attempt #{i}/{self.n_attempt}")
                        sleep(1)
                        ga = GA(allreqs, n_generation=n_generation, thresh=est_max_cap, plot=plot)
                        ga.execute()
                        if not ga.is_converging:
                            continue
                        accepted = iop.loc[iop.index.isin(ga.output), 'timestamp']
                        for ts in accepted:
                            self.loader.update_cell(self.loader.tn_rsv, ('status', 'confirmed'), timestamp=ts, establishment=name)
                        rejected = iop.loc[~iop.index.isin(ga.output), 'timestamp']
                        for ts in rejected:
                            self.loader.update_cell(self.loader.tn_rsv, ('status', 'unsuccessful'), timestamp=ts, establishment=name)
                        break
                    else:
                        for ts in iop['timestamp']:
                            self.loader.update_cell(self.loader.tn_rsv, ('status', 'walk-in'), timestamp=ts, establishment=name)
                    # ga must undergo at least one loop
                    slots = [target_day + timedelta(seconds=est_default_duration*60*i) for i in range(ga.request_outlook.shape[0])]
                    df = pd.DataFrame({'n_person_request': ga.request_outlook, 'n_person_accepted': ga.accepted_outlook})
                    df.index = pd.to_datetime(slots)
                    df = df.resample('H').mean()
                    df = df.apply(round).astype(int)
                    df['hourly'] = df.index.strftime(std_dt_str)
                    df = df.astype(str).reset_index(drop=True)
                    jsonified = json.dumps(df.to_dict()).replace(' ', '')
                    # dfied = pd.DataFrame.from_dict(json.loads(jsonified))
                    # print(dfied)
                    self.loader.add_row(self.loader.tn_rsv_report, timestamp=datetime.strftime(datetime.now(), ts_dt_str), 
                                                                   establishment=name, 
                                                                   hourly=jsonified, 
                                                                   utilization=ga.capacity_percentage, 
                                                                   acceptance=ga.request_acceptance_percentage,
                                                                   source='ga',
                                                                   period=dt_to_str(target_day))
        return None

    def linear_check(self, all_days=False):
        rsv = self.loader.load_from_table(self.loader.tn_rsv)
        rsv['time_in'] = rsv['time_in'].apply(str_to_dt)
        qry = self.loader.load_from_table(self.loader.tn_qry)
        qry = qry.loc[qry['time_in'] != 'None']
        qry['time_in'] = qry['time_in'].apply(str_to_dt)
        businesses = rsv['establishment'].drop_duplicates()
        settings = self.loader.load_from_table(self.loader.tn_est)
        today_midnight = datetime(*datetime.now().timetuple()[:3])
        for business in businesses:
            setting = settings.loc[settings['username'] == business]
            try:
                setting = setting.sort_values('timestamp', ascending=False)
            except KeyError:
                setting = setting.sort_values('id', ascending=False)
            setting = setting.reset_index(drop=True).iloc[0]
            try:
                sublocs = json.loads(setting['sublocs'])
            except json.JSONDecodeError:
                continue
            open_time, close_time = setting['open_time'], setting['close_time']
            open_time, close_time = datetime.strptime(open_time, '%H%M'), datetime.strptime(close_time, '%H%M')
            duration = int(setting['default_duration'])
            n_slot = int((close_time - open_time).seconds / 60 // duration)
            max_util = sum(list(sublocs.values())) * n_slot
            # for all days or not
            if all_days:
                days = rsv
            else:
                days_in_advance = int(setting['days_in_advance'])
                ti = rsv['time_in']
                mask = ti < today_midnight + timedelta(days=days_in_advance+2)
                mask &= today_midnight + timedelta(days=days_in_advance+1) <= ti
                days = rsv.loc[mask]
            days = days.loc[rsv['establishment'] == business, 'time_in'].apply(lambda dt: datetime(year=dt.year, month=dt.month, day=dt.day))
            days = days.drop_duplicates()
            for day in days:
                day = day.to_pydatetime()
                mask = (rsv['time_in'] >= day) & (rsv['time_in'] < day + timedelta(days=1))
                mask &= (rsv['establishment'] == business)
                ersv = rsv.loc[mask]
                # utilization percentage
                utilization = round(100 * ersv['n_person'].astype(int).sum() / max_util)
                # from queries
                op = datetime(*day.timetuple()[:3], *open_time.timetuple()[3:6])
                cl = datetime(*day.timetuple()[:3], *close_time.timetuple()[3:6])
                mask = (qry['time_in'] >= op) & (qry['time_in'] < cl)
                mask &= (qry['establishment'] == business)
                eqry_hourly = qry.loc[mask, ('session', 'n_person', 'time_in')]
                eqry_hourly.index = eqry_hourly['time_in']
                eqry_hourly = eqry_hourly.drop(columns=['time_in'])
                eqry_hourly = eqry_hourly.drop_duplicates()
                eqry_hourly = eqry_hourly.drop(columns=['session']).astype(int)
                eqry_hourly = eqry_hourly.resample('H').sum()
                # from reservations
                hourly = ersv[['n_person']].astype(int).copy()
                hourly.columns = ['n_person_accepted']
                hourly.index = ersv['time_in']
                hourly = hourly.resample('H').sum()
                # reporting period
                period = dt_to_str(hourly.iloc[0].name)
                # merge from qry
                hourly['n_person_request'] = eqry_hourly['n_person']
                hourly['hourly'] = hourly.index.to_series().apply(dt_to_str)
                hourly = hourly.reset_index(drop=True)
                # acceptance percentage
                acceptance = round(100 * hourly['n_person_accepted'].sum() / hourly['n_person_request'].sum())
                # convert to string
                jsonified = json.dumps(hourly[['n_person_request', 'n_person_accepted']].to_dict()).replace(' ', '')
                # save
                # print(jsonified, utilization, acceptance, period)
                self.loader.add_row(self.loader.tn_rsv_report, timestamp=datetime.strftime(datetime.now(), ts_dt_str), 
                                                               establishment=business, 
                                                               hourly=jsonified, 
                                                               utilization=utilization, 
                                                               acceptance=acceptance,
                                                               source='sl',
                                                               period=period)
        return None

    def summarize_query(self, plot=False):
        qry = self.loader.load_from_table(self.loader.tn_qry)
        qry_rep = self.loader.load_from_table(self.loader.tn_qry_report)
        qry['day'] = qry['time_in'].apply(str_to_dt)
        # new_report = []
        for establishment, est_group in qry.groupby('establishment'):
            if plot:
                print(establishment)
                sleep(1)
                group = tqdm(est_group.groupby(est_group['day'].dt.date))
            else:
                group = est_group.groupby(est_group['day'].dt.date)
            for day, day_group in group:
                line = {}
                line['period'] = datetime.strftime(day, '%y/%m/%d')
                line['establishment'] = establishment
                if (line['period'], line['establishment']) in [tuple(pe) for pe in qry_rep[['period', 'establishment']].to_numpy()]:
                    if plot:
                        print('already exist', line['period'], line['establishment'])
                    continue
                line['timestamp'] = datetime.strftime(datetime.now(), ts_dt_str)
                actions = pd.DataFrame([sess_group.sort_values('timestamp', ascending=False).iloc[0] for sess, sess_group in day_group.groupby('session')])
                total = actions.shape[0]
                line['n_total'] = total
                for action, act_group in actions.groupby('action'):
                    pct = 100 * act_group.shape[0] / total
                    line[action] = pct
                    if action not in qry_rep:
                        qry_rep[action] = 0.0
                for empty in set(qry_rep.columns) - set(line):
                    line[empty] = 0.0
                # new_report.append(line)
                qry_rep = qry_rep.append(line, ignore_index=True)
        self.loader.replace_table(self.loader.tn_qry_report, 
                                  [ser.to_dict() for idx, ser in qry_rep.iterrows()], 
                                  columns=list(qry_rep.columns))
        return


class Searcher:
    def __init__(self, data, thresh=10, n_return=5):
        # data.slots dimensions >>> weekly, daily, slotly (datetime object)
        # diff is timedelta, 0 is ideal distance
        diff = data.slots - data.time_in + timedelta(seconds=data.est_default_duration*60)
        # get indices in data.slots where first choice is (data.time_in)
        w, d, s = np.where((timedelta() < diff) & (diff <= timedelta(seconds=data.est_default_duration*60)))
        # first choice address
        self.match_address = np.array([*w, *d, *s]).flatten()
        # first choice datetime
        self.match = data.slots[w, d, s]
        self.wds = w, d, s
        # options is those within threshold, contains addresses/indices to location in self.slots
        options = self.get_match(self.match_address, data.slots.shape, thresh)
        self.options, clashes = {}, {}
        if len(options) == 0:
            self.avail_slots = []
            self.is_clashed = False
            self.is_avail = False
        else:
            # sub location, restaurant seats
            for loc in data.eligible_locs:
                # get clash time for each eligible location as ndarray of datetime object
                loc_clash = data.active_rsv.loc[data.active_rsv['loc'] == loc, 'time_in']
                loc_clash = loc_clash.apply(lambda t: datetime.strptime(t, '%y/%m/%d_%H:%M')).astype('object').to_numpy()
                if loc_clash.shape[0] > 0:
                    # clash exists
                    # create mask, for every clash time get the location in self.slot map
                    mask = reduce(lambda a, b: a | b, [clash == data.slots for clash in loc_clash])
                    # 1D list of clash location tuples
                    loc_clash = list(map(tuple, np.array(np.where(mask)).T))
                    # print(loc_clash)
                    # locations after clashed removed
                    cleared = list(filter(lambda option: option not in loc_clash, options))
                    # print(cleared)
                    # 1D map of clash locations in options
                    clashes[loc] = reduce(lambda a, b: a == b, loc_clash, np.array(options))
                    clashes[loc] = list(map(np.all, clashes[loc]))
                else:
                    # clash not exist
                    cleared = options
                    clashes[loc] = [False] * len(options)
                self.options[loc] = list(map(lambda wds: data.slots[wds[0], wds[1], wds[2]], cleared))
            if len(clashes) == 0:
                self.avail_slots = []
                self.is_clashed = False
            else:
                # 1D mask for options clash
                mask = reduce(lambda a, b: np.array(a) & np.array(b), clashes.values())
                # must be tuples
                clashes = np.array(options, dtype='object')[mask]
                clashes = list(map(tuple, clashes))
                # convert address to datetime and filter out clashes
                avail_slots = [data.slots[adrs[0], adrs[1], adrs[2]] for adrs in options if tuple(adrs) not in clashes]
                # trim to n_return length
                n_return = n_return if len(avail_slots) >= n_return else len(avail_slots)
                # slots to choose and if clash occurs
                self.avail_slots = avail_slots[:n_return]
                self.is_clashed = True if len(clashes) > 0 else False
            self.is_avail = True if self.avail_slots else False

    @staticmethod
    def get_match(wds, shape, thresh):
        # if no match, return empty
        if len(wds) == 0:
            return []
        # create 4D placeholders (original data.slot 3D with 1D of its own index [w, d, s])
        slot_address = np.array(np.array(tuple(product(range(shape[0]), range(shape[1]), range(shape[2]))))).reshape([*shape, 3])
        distance_to_first_choice = slot_address - wds
        # get distances for first choice, absolute
        manhattan_distance = np.array([sum(s) for w in np.abs(distance_to_first_choice) for d in w for s in d]).reshape(shape)
        # accept only those within threshold, shape is now messed up
        within_distance = slot_address[manhattan_distance <= thresh]
        # add first choice index again
        arb_dist = np.abs(within_distance - wds)
        if True:
            # give week more distance/cost, arbitrary
            arb_dist = np.array([arb_dist[:, i] * 1/(i+3) for i in range(3)]).T
        # sort, the lowest cost first
        sorted_within_distance = sorted(zip(within_distance, [sum(d) for d in arb_dist]), key=itemgetter(1))
        return list(map(lambda x: tuple(x[0]), sorted_within_distance))


class Agent:
    '''
    '''
    def __init__(self, session, intent, individual, business, #time_in, n_person,
                 n_weeks_for_booking=4, allocation_multiplier_cap=2, **kwargs):
        
        ts = datetime.strftime(datetime.now(), ts_dt_str)
        self.session = session
        loader = Loader()

        # housekeeping, to be independent
        HouseKeeping(session=self.session)

        # continue from same session, if any
        sess_qry = loader.load_from_table(loader.tn_qry, 
                                          intent=intent, session=session, patron=individual, establishment=business).sort_values('timestamp')
        if 'selection' in kwargs:
            # try to get time_in and n_person from previous corespondence, else assign None
            mask = (sess_qry['time_in'] != 'None') & (sess_qry['time_out'] != 'None') & (sess_qry['n_person'] != 'None')
            prev_time_in_n_person = sess_qry.loc[mask, ['time_in', 'time_out', 'n_person']]
            if prev_time_in_n_person.shape[0] > 0:
                time_in, time_out, n_person = prev_time_in_n_person.tail(1).to_numpy()[0]
                if time_in == 'None':
                    time_in = None
                if time_out == 'None':
                    time_out = None
                if n_person == 'None':
                    n_person = None
            else:
                time_in, time_out, n_person = None, None, None
        elif 'time_in' in kwargs and 'n_person' in kwargs:
            time_in, n_person = kwargs['time_in'], kwargs['n_person']
            if 'time_out' in kwargs:
                time_out = kwargs['time_out']
        else:
            time_in, time_out, n_person = None, None, None

        if is_debug_mode:
            print(sess_qry.sort_values('timestamp')[['step', 'action']])
        # last.step
        if sess_qry.shape[0] > 0:
            self.last_step, self.last_action = sess_qry.sort_values('timestamp')[['step', 'action']].tail(1).to_numpy()[0]
        else:
            self.last_step, self.last_action = None, None

        if is_debug_mode:
            print('last step', self.last_step)
            print(kwargs, time_in, n_person)

        # check if either time_in or n_person has been changed
        is_change = False
        if 'time_in' in kwargs and time_in is not None:
            is_change |= kwargs['time_in'] != time_in
        if 'time_out' in kwargs and time_out is not None:
            is_change |= kwargs['time_out'] != time_out
        if 'n_person' in kwargs and n_person is not None:
            is_change |= kwargs['n_person'] != n_person
        
        # if time_in or n_person has been changed
        if is_debug_mode:
            print('is_change', is_change)
        if is_change:
            # time_in OR n_person has been altered, start from beginning
            self.trim = 0
        else:
            # time_in and n_person no change
            self.trim = int(self.last_step) if self.last_step is not None else 0
        
        if is_debug_mode:
            print('trim', self.trim)

        # load data
        # Searcher class needs data, LoadData has searcher var placeholder
        if time_in is not None and n_person is not None:
            kwargs['time_in'], kwargs['n_person'] = time_in, n_person
            self.data = LoadData(self.session, ts, intent, individual, business, n_weeks_for_booking, allocation_multiplier_cap, **kwargs)
            if self.data.is_ballot:
                self.data.searcher = None
            else:                
                self.data.searcher = Searcher(self.data)
        else:
            self.data = LoadData(self.session, ts, intent, individual, business, n_weeks_for_booking, allocation_multiplier_cap, **kwargs)
            self.data.searcher = None

        # establish rule sequence
        self.intent_rules = IntentRules(intent, self.data, trim=self.trim)
        self.rules = self.intent_rules.rules

        if is_debug_mode:
            print('rules sequence', self.rules)
        
    def check_rules(self): 
        # rule sequence is zero length
        if len(self.rules) == 0:
            self.before_exit('0', '1', 'None')
            return '1', 'End of rules or no rules', str(0 + self.trim)
        execution, step = self.rules.execute()
        if isinstance(execution, bool):
            scode, msg, step = str(execution), 'End of rule checking (success)', str(step)
            action = scode
        else:
            scode, msg, step = *execution.response(), str(step)
            # action = str(execution.__class__).split("'")[1].split('.')[1]
            action = execution.__class__.__name__
        self.before_exit(step, scode, action)
        return str(scode), msg, f"{int(step)}"

    def before_exit(self, step, scode, action):
        if is_debug_mode:
            print('step', step)
            print('scode', scode)
            print('action', action)
        # add to all query table
        QueryEntry(self.data, f"{self.trim + int(step) - int(scode)}", action, self.data.selection)
        # rename session if end is reached
        if len(self.intent_rules.rules_list) > 0 or int(scode) == -1:
            if action == self.intent_rules.rules_list[-1].split('?')[1].split(':')[0] or int(scode) == -1:
                QueryAlter(self.data, 
                           {'session': f"{self.session.split('|')[0]}|{round(datetime.now().timestamp())}|success"}, 
                           {'session': self.session})
        return



##################################################### Utility #####################################################


class Loader:
    def __init__(self):
        # initialize from config
        path_db, self.tn_est, self.tn_pat, self.tn_rsv, self.tn_qry, self.tn_rsv_report, self.tn_qry_report = config_read_db()
        self.conn = sqlite3.connect(path_db)

    # loading using pandas, directly to dataframe
    def load_from_table(self, tn, **criteria):
        if criteria:
            w = ' AND '.join(list(map(lambda kv: f"{kv[0]}='{kv[1]}'", criteria.items())))
            q = f"SELECT * FROM {tn} WHERE {w} ORDER BY id DESC"
        else:
            q = f"SELECT * FROM {tn}"
        df = pd.read_sql_query(q, self.conn)
        self.conn.commit()
        return df

    def update_cell(self, tn, cell, **criteria):
        w = ' AND '.join(list(map(lambda kv: f"{kv[0]}='{kv[1]}'", criteria.items())))
        q = f"UPDATE {tn} SET {cell[0]}='{cell[1]}' WHERE {w}"
        self.conn.cursor().execute(q)
        self.conn.commit()
        return q

    def add_row(self, tn, **payload):
        k = ', '.join([str(i) for i in payload.keys()])
        v = ', '.join([f"'{i}'" for i in payload.values()])
        q = f"INSERT INTO {tn} ({k}) VALUES ({v})"
        self.conn.cursor().execute(q)
        self.conn.commit()
        return q

    def replace_table(self, tn, payloads, columns=None):
        # payload is list of dicts
        if columns is None:
            columns = set(chain.from_iterable([list(payload.keys()) for payload in payloads]))
        cursor = self.conn.cursor()
        cursor.execute(f"DROP TABLE {tn}")
        cursor.execute(f"CREATE TABLE {tn} ({', '.join(columns)})")
        self.conn.commit()
        for payload in payloads:
            self.add_row(tn, **payload)
        return


class LoadData(Loader):
    '''
    '''
    def __init__(self, session, timestamp, intent, individual, business, #time_in, n_person, 
                 n_weeks_for_booking, allocation_multiplier_cap, **kwargs):
        # initiate Loader class
        super().__init__()
        
        # identifiers
        self.session = session
        self.timestamp = timestamp

        # user's request
        # request type (intent)
        self.intent = intent
        # query est pat rsv
        self.individual, self.business = individual, business

        ####################################################################################################

        # TODO: others closed may not be necessary
        # TODO: is_active may not be necessary
        # load establishment settings
        self.est_setting = self.load_from_table(self.tn_est, username=self.business)
        if self.est_setting.shape[0] == 0:
            print('unable to link to establishment db table or table does not have establishment entry')
            raise IndexError
        self.est_setting = self.est_setting.iloc[0].to_dict()
        # store in variables
        self.est_max_capacity = self.est_setting['max_cap']
        self.est_max_group_size = self.est_setting['max_group_size']
        try:
            self.est_sublocs = json.loads(self.est_setting['sublocs'])                      
        except json.JSONDecodeError:
            self.est_sublocs = None
        self.est_days_in_advance = int(self.est_setting['days_in_advance'])             # booking days in advance
        self.est_open_days = sorted([int(i) for i in self.est_setting['open_days']])    # open_days: all integers range 1 to 7, starts Monday
        self.est_open_time = datetime.strptime(self.est_setting['open_time'], '%H%M')   # open/close time, default duration in minutes (int)
        self.est_close_time = datetime.strptime(self.est_setting['close_time'], '%H%M')
        self.est_default_duration = int(self.est_setting['default_duration'])

        ####################################################################################################

        sess_qry = self.load_from_table(self.tn_qry, 
                                        intent=intent, session=session, patron=individual, establishment=business).sort_values('timestamp')
        self.is_first_interaction = True if sess_qry.shape[0] == 0 else False
        self.is_args_given = True if kwargs is not None else False

        # 4 weeks (including today therefore - 1)
        max_search = 7 * n_weeks_for_booking + self.est_days_in_advance #+ 7 - len(self.est_open_days) - 1                  
        # to create slots, start/stop time, from int to datetime object
        range_builder = lambda y, m, d, h0, m0, h1, m1: (datetime(y, m, d, h0, m0), datetime(y, m, d, h1, m1))              
        # datetime parser from string to range of datetime object
        dt_parser = lambda tin, tout: (datetime.strptime(tin, '%y/%m/%d_%H:%M'), datetime.strptime(tout, '%y/%m/%d_%H:%M')) 
        # get available days
        # upcoming business days, open-close pair
        now = datetime.now()
        today_midnight = datetime(now.year, now.month, now.day, 0, 0, 0, 0)#, pytz.timezone('Asia/Singapore'))
        avail_days = [today_midnight + timedelta(days=i) for i in range(self.est_days_in_advance, max_search)]
        avail_days = [day for day in avail_days if day.isoweekday() in self.est_open_days]#[self.est_days_in_advance:]
        self.avail_days = [range_builder(day.year, day.month, day.day, 
                                         self.est_open_time.hour, 
                                         self.est_open_time.minute, 
                                         self.est_close_time.hour, 
                                         self.est_close_time.minute) for day in avail_days]
        # business hours: weekly, daily, slotly in datetime, 3D
        slots = [floor((self.est_close_time-self.est_open_time).seconds/60/self.est_default_duration) for op, cl in self.avail_days]
        zipped = zip(self.avail_days, slots)
        slots = np.array([[opcl[0] + timedelta(seconds=slot*self.est_default_duration*60) for slot in range(slots)] for opcl, slots in zipped])
        self.slots = slots.reshape((n_weeks_for_booking, len(self.est_open_days), slots.shape[1]))

        ####################################################################################################

        # establishment all confirmed reservations from now
        all_rsv = self.load_from_table(self.tn_rsv, establishment=self.business, status='confirmed')
        all_rsv = pd.concat([all_rsv, self.load_from_table(self.tn_rsv, establishment=self.business, status='on-hold')])
        all_rsv = pd.concat([all_rsv, self.load_from_table(self.tn_rsv, establishment=self.business, status='walk-in')]).reset_index(drop=True)
        self.all_rsv = all_rsv.loc[all_rsv['time_in'].apply(str_to_dt) >= datetime.now()]
        # establishment future reservations with patron
        mask = self.all_rsv['time_in'].apply(str_to_dt) >= datetime.now()
        mask &= self.all_rsv['patron'] == self.individual
        self.future_rsv = self.all_rsv[mask]

        ####################################################################################################

        self.is_ballot = self.est_sublocs is None

        # time_in (and time_out) and n_person in kwargs
        if 'time_in' in kwargs and 'n_person' in kwargs:
            # tempus et locus
            self.time_in = datetime.strptime(kwargs['time_in'], '%y/%m/%d_%H:%M')
            self.n_person = int(kwargs['n_person'])

            # time_out, open end booking or not
            if 'time_out' not in kwargs or not self.is_ballot:
                # start time by request, end time is start + offset default
                dd = int(self.est_default_duration)
                self.time_out = self.time_in + timedelta(days=0, hours=0, minutes=dd)
                # print(kwargs)
            else:
                # start time and end time by request
                self.time_out = datetime.strptime(kwargs['time_out'], '%y/%m/%d_%H:%M')

            # establishment reservations between request time
            mask = self.all_rsv['time_in'].apply(str_to_dt) >= self.time_in
            mask &= self.all_rsv['time_out'].apply(str_to_dt) <= self.time_out
            self.active_rsv = self.all_rsv.loc[mask & (self.all_rsv['status'] == 'confirmed')]
            # existing booking between request slot
            self.n_existing = self.active_rsv['n_person'].astype(int).sum()
            # request is within business hours
            is_open = map(lambda opcl: opcl[0] <= self.time_in <= opcl[1] - timedelta(seconds=self.est_default_duration*60), self.avail_days)
            self.is_open = True in list(is_open)
            # get sublocs that within capacity but not too much excess
            if self.est_sublocs is None:
                self.eligible_locs = []
            else:
                n_min, n_max = self.n_person, self.n_person * allocation_multiplier_cap
                eligible_locs = [(k, v) for k, v in self.est_sublocs.items() if n_min <= int(v) <= n_max]
                self.eligible_locs = list(map(itemgetter(0), sorted(eligible_locs, key=itemgetter(1))))
        else:
            self.time_in, self.time_out, self.n_person = None, None, None

        # selection in kwargs
        if 'selection' in kwargs:
            self.selection = kwargs['selection']
            # duplicate
            self.duplicate_req = self.all_rsv.loc[(self.all_rsv['patron'] == self.individual) & (self.all_rsv['status'] == 'confirmed'), ('n_person', 'time_in')].to_numpy()
            if self.selection in self.duplicate_req[:, 1]:
                self.is_duplicate = True
            else:
                self.is_duplicate = False
        else:
            self.selection = None
            self.duplicate_req = None
            self.is_duplicate = None

        ####################################################################################################
        
        # placeholders
        self._searcher = None
        # self._selection = None

    @property
    def searcher(self):
        return self._searcher

    @searcher.setter
    def searcher(self, value):
        self._searcher = value

    # @property
    # def selection(self):
    #     return self._selection

    # @selection.setter
    # def selection(self, value):
    #     self._selection = value


class SaveData:
    '''
    '''
    def __init__(self, table, ent):
        path_db, *_ = config_read_db()
        self.conn = sqlite3.connect(path_db)
        self.table = table
        self.entry = ent
        self.execute()
        self.conn.close()
        # del self.conn
        
    # saving using sql, from dictionary
    def execute(self):
        key = "'" + "', '".join(self.entry.keys()) + "'"
        val = "'" + "', '".join(self.entry.values()) + "'"
        q = f"INSERT INTO {self.table} ({key}) VALUES ({val})"
        try:
            self.conn.cursor().execute(q)
        except sqlite3.OperationalError:
            self.conn.cursor().execute(f"CREATE TABLE IF NOT EXISTS {self.table} ({key})")
            self.conn.cursor().execute(q)
        self.conn.commit()
        return


class Sequence(list):
    '''
    '''
    def add(self, to_add):
        self.append(to_add)

    def execute(self):
        if len(self) > 0:
            pointer = 0
            while pointer < len(self):
                element = self[pointer]
                element.execute()
                element = element.result
                pointer += 1
                if is_debug_mode:
                    print('element', element)
                    print('pointer', pointer)
                if isinstance(element, bool):
                    pass
                    # # boolean, do nothing if True
                    # if not element:
                    #     # False, return
                    #     return False, pointer
                elif isinstance(element, int):
                    # integer, jump to
                    pointer = element + 1
                else:
                    # function or object, return the function or object
                    return element, pointer
            return True, pointer
        else:
            return False, None
    

class RuleCompare:
    ''''''
    def __init__(self, a, op, b, cbt=None, cbf=None):
        self.a, self.b, self.op, self.cbt, self.cbf = a, b, op, cbt, cbf
        self._ops = {'>': (lambda a, b: a > b), 
                     '<': (lambda a, b: a < b), 
                     '>=': (lambda a, b: a >= b), 
                     '<=': (lambda a, b: a <= b), 
                     '==': (lambda a, b: a == b), 
                     '!=': (lambda a, b: a != b), 
                     'is': (lambda a, b: a is b),
                     'in': (lambda a, b: a in b),}
        self.cbt = self._set_callback(cbt, True)
        self.cbf = self._set_callback(cbf, False)

    def _set_callback(self, cb, tf):
        if cb is None:
            return tf
        elif isinstance(cb, Union[int, str].__args__):
            return int(cb) - 1
        else:
            return cb

    def execute(self):
        if self._ops[self.op](self.a, self.b):
            return self.cbt
        else:
            return self.cbf


class IntentRules:
    def __init__(self, intent_type, data, trim=0):
        self.data = data
        rules_dict = config_read_return_dict(intent_type)
        rules_list = [(int(k), v.strip()) for k, v in rules_dict.items()]
        self.rules_list = list(map(lambda kv: kv[1], sorted(rules_list, key=itemgetter(0))))
        rules_list = [self.parse_args(r) for r in self.rules_list]
        self.rules = Sequence(rules_list[trim:])
    
    def parse_args(self, args):
        args = args.split('?')
        if len(args) == 1:
            return globals()[args[0]](self.data)
        else:
            tf = args[1].split(':')
            if_true = tf[0]
            if if_true.isnumeric():
                if_true = int(if_true)
            else:
                if_true = globals()[if_true](self.data) if bool(if_true) else None
            if len(tf) > 1: 
                if_false = tf[1]
                if if_false.isnumeric():
                    if_false = int(if_false)
                else:
                    if_false = globals()[if_false](self.data) if bool(if_false) else None
            else:
                if_false = None
            return globals()[args[0]](self.data, if_true=if_true, if_false=if_false)


class QueryAlter(SaveData):
    def __init__(self, data, new_update, conditions):
        path_db, *_ = config_read_db()
        value = ', '.join([f"{k}='{v}'" for k, v in new_update.items()])
        where = ', '.join([f"{k}='{v}'" for k, v in conditions.items()])
        q = f"UPDATE {data.tn_qry} SET {value} WHERE {where}"
        self.conn = sqlite3.connect(path_db)
        self.execute(q)
        self.conn.close()

    def execute(self, q):
        self.conn.cursor().execute(q)
        self.conn.commit()
        return


class QueryEntry:
    def __init__(self, data, step, action, selection):
        self.ent = Query(data, step, action, selection).value
        self.table = data.tn_qry
        self.execute()

    def execute(self):
        SaveData(self.table, self.ent)
        return 0, f"entry successfully added to database: {self.ent}"


class ReservationEntry:
    def __init__(self, data, status, subloc, slot_time, **kwargs):
        self.ent = Reservation(data, status, subloc, slot_time, **kwargs).value
        self.table = data.tn_rsv
        self.execute()

    def execute(self):
        SaveData(self.table, self.ent)
        return 0, f"entry successfully added to database: {self.ent}"


#################################################### Container ####################################################


class Base:
    def __init__(self, data):
        columns = ['session', 'timestamp',
                   'patron', 'establishment', 
                   'n_person', 'time_in', 'time_out', 'intent']
        entry = dict(zip(columns, ['_' for _ in range(len(columns))]))
        entry['timestamp'] = data.timestamp
        entry['session'] = data.session
        entry['patron'] = data.individual
        entry['establishment'] = data.business
        entry['n_person'] = 'None' if data.n_person is None else str(data.n_person)
        entry['time_in'] = 'None' if data.time_in is None else data.time_in.strftime('%y/%m/%d_%H:%M')
        entry['time_out'] = 'None' if data.time_out is None else data.time_out.strftime('%y/%m/%d_%H:%M')
        entry['intent'] = data.intent
        self.value = entry


class Query(Base):
    def __init__(self, data, step, action, selection):
        super().__init__(data)
        self.value['step'] = step
        self.value['action'] = action
        self.value['selection'] = 'None' if selection is None else selection


class Reservation(Base):
    def __init__(self, data, status, subloc, slot_time, **kwargs):
        super().__init__(data)
        self.value['status'] = status
        self.value['loc'] = subloc
        self.value['time_in'] = slot_time
        if 'slot_time_end' in kwargs:
            self.value['time_out'] = kwargs['slot_time_end']


###################################################### Rules ######################################################


class RuleBase:
    def __init__(self, data, if_true=None, if_false=None):
        self.data = data
        self.if_true = if_true
        self.if_false = if_false
        self.result = None


class Dummy:
    def __init__(self, data, if_true=None, if_false=None):
        self.result = NotImplemented(data)


class WithinBookableWindow(RuleBase):
    def execute(self):
        self.result = RuleCompare(self.data.is_open, '==', True, self.if_true, self.if_false).execute()


class WithinCapacity(RuleBase):
    def execute(self):
        self.result = RuleCompare(self.data.n_existing + self.data.n_person, '<=', self.data.est_max_capacity, 
                                  self.if_true, self.if_false).execute()


class WithinGroupSize(RuleBase):
    def execute(self):
        self.result = RuleCompare(self.data.n_person, '<=', self.data.est_max_group_size, self.if_true, self.if_false).execute()


class IsDuplicateExist(RuleBase):
    def execute(self):
        self.result = RuleCompare(self.data.is_duplicate, '==', True, self.if_true, self.if_false).execute()


class SlotsAvailable(RuleBase):
    def execute(self):
        self.result = RuleCompare(self.data.searcher.is_avail, '==', True, self.if_true, self.if_false).execute()


class SlotAvailable(RuleBase):
    def execute(self):
        self.result = RuleCompare(self.data.searcher.is_clashed, '==', False, self.if_true, self.if_false).execute()


class SlotNotSelected(RuleBase):
    def execute(self):
        is_not_selecting = self.data.selection is None or self.data.selection == ' None'
        if not is_not_selecting:
            if self.data.searcher is not None:
                is_not_selecting |= str_to_dt(self.data.selection) not in self.data.searcher.avail_slots
            elif self.data.is_ballot:
                try:
                    slots = list(filter(lambda slot: self.data.time_in <= slot < self.data.time_out, self.data.slots.flatten()))
                    is_not_selecting |= slots[0] != str_to_dt(self.data.selection)
                except TypeError:
                    loader = Loader()
                    rsv = loader.load_from_table(loader.tn_rsv, status='confirmed')
                    rsv = pd.concat([rsv, loader.load_from_table(loader.tn_rsv, status='on-hold')])
                    rsv = pd.concat([rsv, loader.load_from_table(loader.tn_rsv, status='walk-in')]).reset_index(drop=True)
                    rsv = rsv.loc[rsv['time_in'].apply(str_to_dt) >= datetime.now(), 'time_in'].to_numpy()
                    is_not_selecting != self.data.selection not in rsv
        self.result = RuleCompare(is_not_selecting, '==', True, self.if_true, self.if_false).execute()


class IsUpcomingExist(RuleBase):
    def execute(self):
        self.result = RuleCompare(self.data.future_rsv.shape[0], '>', 0, self.if_true, self.if_false).execute()


class IsValidSelection(RuleBase):
    '''is selection in future_rsv time_in'''
    def execute(self):
        self.result = RuleCompare(np.any(self.data.future_rsv['time_in'].isin([self.data.selection])), '==', True, 
                                  self.if_true, self.if_false).execute()


class IsTooSoon(RuleBase):
    def execute(self):
        req_date = self.data.time_in
        req_date = datetime(year=req_date.year, month=req_date.month, day=req_date.day, hour=0, minute=0, second=0)
        now_date = datetime.now()
        now_date = datetime(year=now_date.year, month=now_date.month, day=now_date.day, hour=0, minute=0, second=0)
        self.result = RuleCompare((req_date - now_date).days, '<', self.data.est_days_in_advance, self.if_true, self.if_false).execute()


class IsInThePast(RuleBase):
    def execute(self):
        self.result = RuleCompare(self.data.time_in, '<=', datetime.now(), self.if_true, self.if_false).execute()


class WithinOperatingHours(RuleBase):
    def execute(self):
        hhmm = datetime.strptime(f"{self.data.time_in.hour}{self.data.time_in.minute}", '%H%M')
        is_in_between = self.data.est_open_time <= hhmm <= self.data.est_close_time
        self.result = RuleCompare(is_in_between, '==', True, self.if_true, self.if_false).execute()


class WithinOpenDays(RuleBase):
    def execute(self):
        self.result = RuleCompare(self.data.time_in.isoweekday(), 'in', self.data.est_open_days, self.if_true, self.if_false).execute()


class IsTimeout(RuleBase):
    '''it is assumed to be timeout if selection appears after housekeeping timed out the session, cannot select in first interaction'''
    def execute(self):
        is_timeout = self.data.is_first_interaction and self.data.selection is not None
        self.result = RuleCompare(is_timeout, '==', True, self.if_true, self.if_false).execute()


class IsArgsGiven(RuleBase):
    def execute(self):
        self.result = RuleCompare(self.data.is_args_given, '==', True, self.if_true, self.if_false).execute()


class IsHistory(RuleBase):
    def execute(self):
        loader = Loader()
        rsv_w_patron = loader.load_from_table(loader.tn_rsv, establishment=self.data.business, patron=self.data.individual)
        rsv_w_patron = rsv_w_patron.loc[rsv_w_patron['time_in'].apply(str_to_dt) >= datetime.now()]
        self.result = RuleCompare(rsv_w_patron.shape[0], '>', 0, self.if_true, self.if_false).execute()


class IsBallot(RuleBase):
    def execute(self):
        self.result = RuleCompare(self.data.is_ballot, '==', True, self.if_true, self.if_false).execute()


class ExecuteTrueOnly(RuleBase):
    def execute(self):
        self.result = RuleCompare(True, '==', True, self.if_true, self.if_false).execute()


class IsTOEarlierThanTI(RuleBase):
    def execute(self):
        self.result = RuleCompare(self.data.time_out, '<=', self.data.time_in, self.if_true, self.if_false).execute()


##################################################### Actions #####################################################

#  0 success
#  1 fail
# -1 terminating signal

class Message:
    def __init__(self, data, *args, **kwargs):
        self.data = data
        self.args = args
        self.kwargs = kwargs

    def response(self):
        return -1, 'Returning default response message'


class NotImplemented(Message):
    def response(self):
        return -1, 'Not implemented'


# class Success(Message):
#     def response(self):
#         return 0, 'success'


class OutsideBookableWindow(Message):
    def response(self):
        return 1, 'Your request is outside bookable window'


class OverCapacity(Message):
    def response(self):
        return 1, 'I am afraid our full capacity has been reached'


class OversizedGroup(Message):
    def response(self):
        return 1, f"Your request for {self.data.n_person} number of people is too big. Only up to {self.data.est_max_group_size} people allowed"


class DuplicateExist(Message):
    def response(self):
        return 1, 'You already have upcoming reservation slot(s): \n' + '\n'.join([f'for {q} on {t}' for q, t in self.data.duplicate_req])


class PlaceNotAvail(Message):
    def response(self):
        return -1, 'I am afraid no slots available'


class TooSoon(Message):
    def response(self):
        return 1, f"Please make reservation {self.data.est_days_in_advance} day(s) in advance"


class UpcomingNotExist(Message):
    def response(self):
        return 1, 'You do not have future reservations'


class SelectionNotValid(Message):
    def response(self):
        return 1, 'Please affirm if the proposed slot is okay' if self.data.is_ballot else 'Please choose from proposed slot(s)'


class InputNotValid(Message):
    def response(self):
        return 1, 'Your input not valid'


class InThePast(Message):
    def response(self):
        return 1, 'Your request time is in the past'


class OutsideOperatingHours(Message):
    def response(self):
        return 1, 'Your request time is outside our operating hours'


class OutsideOpenDays(Message):
    def response(self):
        return 1, 'I am afraid we are not open on that day'


class Timeout(Message):
    def response(self):
        return 1, 'Your previous session has timed out. I am afraid you need to start over'


class NoTimeInAndNPersonGiven(Message):
    def response(self):
        return 1, 'Please advise me with your desired reservation time and number of guests'


class CancelSuccess(Message):
    def response(self):
        loader = Loader()
        loader.update_cell(loader.tn_rsv, ('status', 'cancelled'), time_in=self.data.selection)
        return -1, 'The reservation has been successfully cancelled'


class Bye(Message):
    def response(self):
        return -1, 'Thanks for using Ira. Good bye'


class OfferSlots(Message):
    def response(self):
        adapted_list = [f"({i+1}) {datetime.strftime(slot, '%A %d %B %Y at %H:%M')}" for i, slot in enumerate(self.data.searcher.avail_slots)]
        return 0, 'Available time slot(s): \n' + '\n'.join(adapted_list)


class FinalizeReservation(Message):
    def response(self):
        selection = str_to_dt(self.data.selection)
        for subloc, slots in self.data.searcher.options.items():
            if selection in slots:
                ReservationEntry(self.data, 'confirmed', subloc, self.data.selection)
                # terminate session
                # QueryAlter(self.data, 
                #            {'session': f"{self.data.session.split('|')[0]}|{round(datetime.now().timestamp())}|success"}, 
                #            {'session': self.data.session})
                return -1, f"Reservation for {self.data.n_person} on {datetime.strftime(selection, '%A %d %B %Y at %H:%M')} has been confirmed"


class OnHoldReservation(Message):
    def response(self):
        selection = str_to_dt(self.data.selection)
        loader = Loader()
        qry = loader.load_from_table(loader.tn_qry, session=self.data.session).sort_values('timestamp', ascending=False)
        qry = qry.loc[(qry['time_in'] != 'None') & (qry['time_out'] != 'None')].reset_index(drop=True).iloc[0]
        time_in, time_out = str_to_dt(qry['time_in']), str_to_dt(qry['time_out'])
        slots = list(filter(lambda slot: time_in <= slot < time_out, self.data.slots.flatten()))
        offset_seconds = timedelta(seconds=int(self.data.est_default_duration)*60)
        if len(slots) > 1:
            start, end = slots[0], slots[-1] + offset_seconds
        else:
            start, end = slots[0], slots[0] + offset_seconds
        ReservationEntry(self.data, 'on-hold', 'None', dt_to_str(start), slot_time_end=dt_to_str(end))
        # terminate session
        # QueryAlter(self.data, 
        #             {'session': f"{self.data.session.split('|')[0]}|{round(datetime.now().timestamp())}|success"}, 
        #             {'session': self.data.session})
        # message
        start = datetime.strftime(start, '%A %d %B %Y at %H:%M')
        end = datetime.strftime(end, '%H:%M')
        msg = f"Your request for {self.data.n_person} person(s) on {start} to {end} is now on-hold. "
        close_hour = str(self.data.est_close_time.hour).zfill(2)
        close_minute = str(self.data.est_close_time.minute).zfill(2)
        msg += f"Please status check after cufoff time {close_hour}:{close_minute}"
        return -1, msg


class ListUpcoming(Message):
    def response(self):
        to_adapt = list(map(str_to_dt, self.data.future_rsv['time_in'].to_numpy()))
        adapted_list = [f"({i+1}) {datetime.strftime(time_in, '%A %d %B %Y at %H:%M')}" for i, time_in in enumerate(to_adapt)]
        return 0, 'Please choose from the upcoming reservation slot(s): \n' + '\n'.join(adapted_list)


class InquireNewSlot(Message):
    def response(self):
        return 0, 'How many persons would need to be admitted at which date and time, please?'


class ChangeReservation(Message):
    def response(self):
        loader = Loader()
        old_selection = loader.load_from_table(loader.tn_qry, session=self.data.session).sort_values('timestamp')
        old_selection = old_selection.loc[old_selection['selection'] != 'None', 'selection'].to_numpy()[0]
        loader.update_cell(loader.tn_rsv, ('status', 'changed'), time_in=old_selection)
        selection = str_to_dt(self.data.selection)
        for subloc, slots in self.data.searcher.options.items():
            if selection in slots:
                ReservationEntry(self.data, 'confirmed', subloc, self.data.selection)
                break
        old_selection = datetime.strftime(str_to_dt(old_selection), '%A %d %B %Y at %H:%M')
        msg = f"Previous reservation on {old_selection} has been successfully cancelled, "
        new_selection = datetime.strftime(str_to_dt(self.data.selection), '%A %d %B %Y at %H:%M')
        msg += f"and new reservation for {self.data.n_person} on {new_selection} has been confirmed"
        return -1, msg


class ListHistory(Message):
    def insight(self, loader, day, time_in):
        # only ga produces 'unsuccessful'
        df = loader.load_from_table(loader.tn_rsv_report, source='ga')
        df = df.loc[df['period'].apply(lambda dt: dt.split('_')[0]) == day].sort_values('timestamp', ascending=False).iloc[0]
        utilization = df['utilization']
        acceptance = df['acceptance']
        jsonified = df['hourly']
        dfied = pd.DataFrame.from_dict(json.loads(jsonified))
        leastbz = dfied.sort_values('n_person_accepted')['hourly'][0].split('_')[1]
        leastbz2nd = dfied.sort_values('n_person_accepted')['hourly'][1].split('_')[1]
        # day = datetime.strftime(datetime.strptime(day, '%y/%m/%d'), '%A %d %B %Y')
        msg = f"I am afraid your request for {time_in} is not among the {acceptance}% that were accepted."
        msg += '\n' + f"We are at {utilization}% capacity on this day."
        msg += '\n' + f"It is advised to do a walk-in at our least busy hour at {leastbz} or {leastbz2nd}."
        return msg

    def response(self):
        loader = Loader()
        rsv_w_patron = loader.load_from_table(loader.tn_rsv, establishment=self.data.business, patron=self.data.individual)
        rsv_w_patron = rsv_w_patron.loc[rsv_w_patron['time_in'].apply(str_to_dt) >= datetime.now()]
        dy = rsv_w_patron['time_in'].apply(lambda dt: dt.split('_')[0])
        ti = rsv_w_patron['time_in'].apply(lambda dt: datetime.strftime(str_to_dt(dt), '%A %d %B %Y at %H:%M')).to_numpy()
        to = rsv_w_patron['time_out'].apply(lambda dt: datetime.strftime(str_to_dt(dt), '%H:%M')).to_numpy()
        pn = rsv_w_patron['n_person'].to_numpy()
        st = rsv_w_patron['status'].to_numpy()
        iop = np.array([np.arange(1, pn.shape[0] + 1), dy, ti, to, pn, st]).T
        msg_builder = lambda i, dy, ti, to, pn, st: f"({i}) {ti} to {to} for {pn} person(s) is {st}"
        msg = ''
        for row in iop:
            msg += '\n' + msg_builder(*row)
            status, day, time_in = row[-1], row[1], row[2]
            if status == 'unsuccessful':
                # only ga produces 'unsuccessful'
                msg += '\n' + self.insight(loader, day, time_in)
        return -1, 'You have these reservation(s):' + msg


class ListEmpty(Message):
    def response(self):
        return -1, 'You do not have any reservation history'


class InformBallotSlot(Message):
    def response(self):
        # slots is 3D, week day slot
        slots = list(filter(lambda slot: self.data.time_in <= slot < self.data.time_out, self.data.slots.flatten()))
        offset_seconds = timedelta(seconds=int(self.data.est_default_duration)*60)
        if len(slots) > 1:
            start, end = slots[0], slots[-1] + offset_seconds
        else:
            start, end = slots[0], slots[0] + offset_seconds
        start, end = datetime.strftime(start, '%A %d %B %Y at %H:%M'), datetime.strftime(end, '%H:%M')
        return 0, f"Time frame that fits your preferences is {start} to {end}. Please confirm if it's okay for you"


class UnableToChange(Message):
    def response(self):
        return -1, 'I am afraid your reservation can only be cancelled. You may apply for the new one'


class TOEarlierThanTI(Message):
    def response(self):
        return 1, 'Exit time should not be earlier than entry time'


################################################ Genetic Algorithm ################################################


class GA:
    def __init__(self, population, n_generation, thresh, 
                 batch=20, convergence_rate=0.95, crossover_rate=0.25, crossover_point=0.5, mutation_rate=0.25, min_generation=0.5, 
                 plot=True):
        self.allreqs = population
        self.n_generation = n_generation
        self.thresh = thresh
        self.convergence_rate = convergence_rate
        self.crossover_rate = crossover_rate
        self.crossover_point = crossover_point
        self.mutation_rate = mutation_rate
        self.min_generation = min_generation
        self.plot = plot
        # initial population created randomly, shape is (batch, n_req)
        # e.g. initpop[0]
        # array([1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 1, 1, 1,
        #        0, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0, 0, 1, 1, 1, 0, 1, 1, 0,
        #        1, 1, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1,
        #        1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 1, 1, 1,
        #        1, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1])
        # initpop literal only true for initiation, subsequently it is no longer holding inital values
        self.initpop = np.array([[np.random.randint(2) for _ in range(len(population))] for r_ in range(batch)])
        # parent qty is half the offspring
        self.n_parent = int(batch / 2)
        self.n_offspring = batch - self.n_parent
        self.output = None
        self.is_converging = True

    def fitness(self):
        # population is group of masks (0/1) for which members of population is selected
        def get_score(select):
            # need pop and thresh from parent function
            slot_wise = np.array([self.allreqs[i] if s == 1 else np.zeros(self.allreqs.shape[1]) for i, s in enumerate(select)]).T
            sums = np.array([sum(s) for s in slot_wise])
            sums = -sum(sums) if np.any([sums > self.thresh]) else sum(sums)
            return sums
        scores = np.array(list(map(get_score, self.initpop))).astype(int)
        return scores 

    # parent
    def selection(self, f):
        f = list(f)
        parents = np.empty((self.n_parent, self.initpop.shape[1]))
        for i in range(self.n_parent):
            max_fitness_idx = np.where(f == np.max(f))
            parents[i,:] = self.initpop[max_fitness_idx[0][0], :]
            f[max_fitness_idx[0][0]] = 0
        return parents

    # offspring, crossover point is hardcoded as half
    def crossover(self, parents):
        # parents, n_offspring
        # parents.shape[1] is n_req
        offsprings = np.empty((self.n_offspring, parents.shape[1]))
        # crossover at half
        crossover_point = int(parents.shape[1] / 2)
        for i in range(self.n_offspring):
            # choose parent1, start from the fittest
            j = randint(0, int(parents.shape[0]/2))
            while j < parents.shape[0]:
                if rd.random() < self.crossover_rate:
                    j += 1
                    continue
                parent1_index = j % parents.shape[0]
                break
            else:
                parent1_index = 0
            j = randint(int(parents.shape[0]/2), parents.shape[0])
            # choose parent2, start from runner-up
            while j < parents.shape[0]:
                if rd.random() < self.crossover_rate:
                    j += 1
                    continue
                parent2_index = j % parents.shape[0]
                break
            else:
                parent2_index = 1
            # cross parents
            offsprings[i, :crossover_point] = parents[parent1_index, :crossover_point]
            offsprings[i, crossover_point:] = parents[parent2_index, crossover_point:]
        return offsprings

    def mutation(self, offsprings):
        mutants = np.empty((offsprings.shape))
        for i in range(mutants.shape[0]):
            mutants[i, :] = offsprings[i, :]
            if rd.random() > self.mutation_rate:
                # no mutation
                continue
            # mutate, toggle
            idx = randint(0, offsprings.shape[1] - 1) 
            mutants[i, idx] = 1 if mutants[i, idx] == 0 else 0
        return mutants

    def optimize(self):
        # reqs is allreqs
        # population is initpop
        # pop_size.shape is (batch, n_req)
        # num_generations is number of iterations
        # threshold is self explanatory
        parameters, fitness_history = [], []
        iterator = tqdm(range(self.n_generation)) if self.plot else range(self.n_generation)
        for i in iterator:
            # get scores
            f = self.fitness()
            fitness_history.append(f)
            # select group of fittest (high scoring) parents
            parents = self.selection(f)
            # cross parents for offsprings
            offsprings = self.crossover(parents)
            # mutate offsprings
            mutants = self.mutation(offsprings)
            # merge midway
            self.initpop[:self.n_parent, :] = parents
            self.initpop[self.n_offspring:, :] = mutants
            # early break
            cts = list(f).count(f.max())
            # end early, all scores are greater than zero AND majority is above convergence_rate AND more than min number of gen
            if np.all(f > 0) and cts / f.shape[0] >= self.convergence_rate and i / self.n_generation >= self.min_generation:
                if self.plot:
                    print(f"Convergence at or above {round(self.convergence_rate * 100)}% after {i} generations")
                break
        else:
            # no convergence
            if self.plot:
                print('Not converging')
                self.is_converging = False
            
        fitness_last_gen = f#self.fitness()
        max_fitness = np.where(fitness_last_gen == np.max(fitness_last_gen))
        parameters.append(self.initpop[max_fitness[0][0], :])
        if self.plot:
            print('Last generation: \n{}\n'.format(self.initpop)) 
            print('Fitness of the last generation: \n{}\n'.format(fitness_last_gen))
        return parameters, fitness_history, i

    def execute(self):
        parameters, fitness_history, n_generation = self.optimize()
        request_outlook = np.array([sum(trow) for trow in self.allreqs.T]).astype(int)
        self.request_outlook = request_outlook
        if not self.is_converging:
            self.output = None
            self.accepted_outlook = None
            self.capacity_percentage = None
            self.request_acceptance_percentage = None
            # print('No solution. First gen may have been all zero')
            return None
        parameters = parameters[0]
        selected_items = np.where(parameters > 0)[0]
        accepted_outlook = np.array([sum(trow) for trow in np.array([self.allreqs[i] for i in selected_items]).T]).astype(int)
        self.request_acceptance_percentage = round(100 * selected_items.shape[0] / self.allreqs.shape[0])
        self.capacity_percentage = round(100 * sum(accepted_outlook) / self.thresh / self.allreqs.shape[1])
        if self.plot:
            print('The optimized parameters for the given inputs are: \n{}\n'.format(parameters))
            print('Accepted requests:', selected_items, '\n')
            fitness_history_mean = [np.mean(f) for f in fitness_history]
            fitness_history_max = [np.max(f) for f in fitness_history]
            plt.plot(list(range(n_generation+1)), fitness_history_mean, label='Mean Fitness')
            plt.plot(list(range(n_generation+1)), fitness_history_max, label='Max Fitness')
            plt.legend()
            plt.title('Fitness through the generations')
            plt.xlabel('Generations')
            plt.ylabel('Fitness')
            plt.show()
            print(np.asarray(fitness_history).shape)
            print('\nThreshold outlook:')
            for i, comparison in enumerate(['\trequest {},\taccepted {}'.format(*z) for z in zip(request_outlook, accepted_outlook)]):
                print(i + 1, comparison)
            print('\n{}% utilization\n'.format(self.capacity_percentage))
            print('{}% requests served\n\n'.format(self.request_acceptance_percentage))
        self.output = selected_items
        self.accepted_outlook = accepted_outlook
        return selected_items