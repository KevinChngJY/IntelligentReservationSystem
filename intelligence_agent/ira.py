import pytz
import json
import config
import sqlite3
import numpy as np
import pandas as pd
from typing import Union
from functools import reduce
from math import ceil, floor
from types import FunctionType
from operator import itemgetter
from genetic_algorithm import GA
from itertools import product, chain
from datetime import datetime, timedelta


str_to_dt = lambda dt: datetime.strptime(dt, '%y/%m/%d_%H:%M')
dt_to_str = lambda dt: datetime.strftime(dt, '%y/%m/%d_%H:%M')
is_debug_mode = False


class HouseKeeping:
    # 1. free up on-hold, rsv
    def __init__(self, timeout=60, **kwargs):
        self.timeout = timeout
        self.loader = Loader()
        if 'session' in kwargs:
            self.session = kwargs['session']
            self.timeout_check()
            self.expired_check()
        else:
            # self.genetic_algorithm_check()
            self.n_attempt = 3

    def timeout_check(self):
        on_hold = self.loader.load_from_table(self.loader.tn_qry)
        # on_hold = on_hold.loc[~on_hold['session'].str.contains('|')]
        on_hold = on_hold.loc[on_hold['session'].apply(lambda sess: True if '|' not in sess else False)]
        for _, row in on_hold.iterrows():
            if datetime.now() - datetime.strptime(row['timestamp'],'%y/%m/%d_%H:%M:%S.%f') > timedelta(seconds=self.timeout):
                # session expires
                expired_sess = f"{self.session.split('|')[0]}|{round(datetime.now().timestamp())}|timeout"
                self.loader.update_cell(self.loader.tn_qry, ('session', expired_sess), **row.to_dict())
        return

    def expired_check(self):
        on_hold = self.loader.load_from_table(self.loader.tn_rsv)
        on_hold.loc[on_hold['time_out'].apply(str_to_dt) < datetime.now(), 'status'] = 'completed'
        return

    # n_generation is hardcoded
    def genetic_algorithm_check(self, n_generation=1000):
        on_hold = self.loader.load_from_table(self.loader.tn_rsv)
        on_hold = on_hold.loc[on_hold['status'] == 'on-hold']
        hm_parser = lambda hm: datetime.strptime(hm, '%H%M')
        # for every establishment
        for i, g in on_hold.groupby('establishment'):
            # load establishment setting
            est = self.loader.load_from_table(self.loader.tn_est)
            try:
                est = est.loc[est['username'] == i].sort_values('timestamp', ascending=False).reset_index(drop=True).iloc[0]
            except KeyError:
                est = est.loc[est['username'] == i].sort_values('index', ascending=False).reset_index(drop=True).iloc[0]
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
            iop = g.loc[g['time_in'].apply(str_to_dt) < today_midnight + timedelta(days=est_days_in_advance+2), 
                        ['timestamp', 'time_in', 'time_out', 'n_person']].copy().astype('object').reset_index(drop=True)
            n_req = iop.shape[0]
            # time_in and time_out have day month year
            iop['time_in'] = iop['time_in'].apply(lambda ymd_hm: hm_parser(ymd_hm.split('_')[1].replace(':', '')))
            iop['time_out'] = iop['time_out'].apply(lambda ymd_hm: hm_parser(ymd_hm.split('_')[1].replace(':', '')))
            open_time = iop['time_in'].apply(lambda ti: datetime(year=ti.year, month=ti.month, day=ti.day, 
                                                                 hour=open_time.hour, minute=open_time.minute, second=open_time.second))
            start = (iop['time_in'] - open_time).apply(lambda s: s.seconds // (est_default_duration * 60)).tolist()
            n_block = (iop['time_out'] - iop['time_in']).apply(lambda diff: diff.seconds // (est_default_duration * 60)).tolist()
            n_person = iop['n_person'].astype(int).tolist()
            # build allreqs
            allreqs = np.zeros((n_req, n_slot))
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
                    print(f"Attempt #{i}/{self.n_attempt}")
                    ga = GA(allreqs, n_generation=n_generation, thresh=est_max_cap, plot=True)
                    ga.execute()
                    if ga.output is None:
                        continue
                    accepted = iop.loc[iop.index.isin(ga.output), 'timestamp']
                    for ts in accepted:
                        self.loader.update_cell(self.loader.tn_rsv, ('status', 'confirmed'), timestamp=ts)
                    rejected = iop.loc[~iop.index.isin(ga.output), 'timestamp']
                    for ts in rejected:
                        self.loader.update_cell(self.loader.tn_rsv, ('status', 'unsuccessful'), timestamp=ts)
                    break
                else:
                    for ts in iop['timestamp']:
                        self.loader.update_cell(self.loader.tn_rsv, ('status', 'walk-in'), timestamp=ts)


class Searcher:
    def __init__(self, data, thresh=10, n_return=5):
        diff = data.slots - data.time_in + timedelta(seconds=data.est_default_duration*60)
        w, d, s = np.where((timedelta() < diff) & (diff <= timedelta(seconds=data.est_default_duration*60)))
        # first choice address
        self.match_address = np.array([*w, *d, *s]).flatten()
        # first choice datetime
        self.match = data.slots[w, d, s]
        self.wds = w, d, s
        # options is those within threshold, contains addresses/indices to location in self.slots
        options = self.get_adjacent(self.match_address, data.slots.shape, thresh, n_return)
        self.options, clashes = {}, {}
        if len(options) == 0:
            self.avail_slots = []
            self.is_clashed = False
            self.is_avail = False
        else:
            # sub location
            if True:
                # restaurant seats
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
            else:
                # TODO: concert admittance, one giant loc
                self.options[data.est_setting['name']] = data.n_person
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
    def get_adjacent(wds, shape, thresh, n_return):
        if len(wds) == 0:
            return []
        slot_address = np.array(np.array(tuple(product(range(shape[0]), range(shape[1]), range(shape[2]))))).reshape([*shape, 3])
        distance_to_first_choice = slot_address - wds
        manhattan_distance = np.array([sum(s) for w in np.abs(distance_to_first_choice) for d in w for s in d]).reshape(shape)
        within_distance = slot_address[manhattan_distance < thresh + 1]
        arb_dist = np.abs(within_distance - wds)
        if True:
            # give week more distance, arbitrary
            arb_dist = np.array([arb_dist[:, i] * 1/(i+3) for i in range(3)]).T
        sorted_within_distance = sorted(zip(within_distance, [sum(d) for d in arb_dist]), key=itemgetter(1))
        return list(map(lambda x: tuple(x[0]), sorted_within_distance))


class Agent:
    '''
    '''
    def __init__(self, session, intent, individual, business, #time_in, n_person,
                 n_weeks_for_booking=4, allocation_multiplier_cap=2, **kwargs):
        
        ts = datetime.strftime(datetime.now(), '%y/%m/%d_%H:%M:%S.%f')
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


class KD():
    '''

    '''
    def __init__(self):
        pass


##################################################### Utility #####################################################


class Loader:
    def __init__(self):
        # initialize from config
        path_db, self.tn_est, self.tn_pat, self.tn_rsv, self.tn_qry = config.read_db()
        self.conn = sqlite3.connect(path_db)

    # loading using pandas, directly to dataframe
    def load_from_table(self, tn, **criteria):
        if criteria:
            w = ' AND '.join(list(map(lambda kv: f"{kv[0]}='{kv[1]}'", criteria.items())))
            q = f"SELECT * FROM {tn} WHERE {w} ORDER BY id DESC"
        else:
            q = f"SELECT * FROM {tn}"
        df = pd.read_sql_query(q, self.conn)
        return df

    def update_cell(self, tn, cell, **criteria):
        w = ' AND '.join(list(map(lambda kv: f"{kv[0]}='{kv[1]}'", criteria.items())))
        q = f"UPDATE {tn} SET {cell[0]}='{cell[1]}' WHERE {w}"
        self.conn.cursor().execute(q)
        self.conn.commit()
        return q


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
            self.active_rsv = self.all_rsv.loc[mask]
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
            self.duplicate_req = self.all_rsv.loc[self.all_rsv['patron'] == self.individual, ('n_person', 'time_in')].to_numpy()
            if self.selection in self.duplicate_req[:, 1]:
                self.is_duplicate = True
            else:
                self.is_duplicate = False
        else:
            self.selection = None
            self.duplicate_req = None

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
        path_db, *_ = config.read_db()
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
        rules_dict = config.read_return_dict(intent_type)
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
        path_db, *_ = config.read_db()
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
        if self.data.searcher is not None:
            is_not_selecting |= self.data.selection not in [dt_to_str(slot) for slot in self.data.searcher.avail_slots]
        if self.data.is_ballot and not is_not_selecting:
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
        self.result = RuleCompare(self.data.all_rsv.shape[0], '>', 0, self.if_true, self.if_false).execute()


class IsBallot(RuleBase):
    def execute(self):
        self.result = RuleCompare(self.data.is_ballot, '==', True, self.if_true, self.if_false).execute()


class ExecuteTrueOnly(RuleBase):
    def execute(self):
        self.result = RuleCompare(True, '==', True, self.if_true, self.if_false).execute()


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
        return 1, 'I am afraid no slots available'


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
        return 1, 'The reservation has been successfully cancelled'


class Bye(Message):
    def response(self):
        return 0, 'Thanks for using Ira. Good bye'


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
                return 0, f"Reservation for {self.data.n_person} on {datetime.strftime(selection, '%A %d %B %Y at %H:%M')} has been confirmed"


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
        return 0, msg


class ListHistory(Message):
    def response(self):
        ti = self.all_rsv['time_in'].apply(lambda dt: str_to_dt(df), '%A %d %B %Y at %H:%M').to_numpy()
        to = self.all_rsv['time_out'].apply(lambda dt: str_to_dt(df), '%H:%M').to_numpy()
        pn = self.all_rsv['n_person'].to_numpy()
        st = self.all_rsv['status'].to_numpy()
        iop = np.array([np.arange(1, pn.shape[0] + 1), ti, to, pn, st]).T
        iop = '\n'.join([f"({i}) {ti} to {to} for {pn} person(s) is {st}" for i, ti, to, pn, st in iop])
        return 0, 'You these reservation(s):\n' + iop


class ListEmpty(Message):
    def response(self):
        return 0, 'You do not have any reservation history'


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
        return 0, f"The time frame that falls within your preferences is {start} to {end}. Please confirm if it's okay for you"


class UnableToChange(Message):
    def response(self):
        return -1, 'I am afraid your reservation can only be cancelled'
