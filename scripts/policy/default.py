import datetime
import time
import statistics
import json
import os

class Policy():
    def __init__(self, path, dvpns={}):
        print('Policy.init', path, dvpns)
        self.path = path
        self.dvpns = dvpns

        self.ready = {d: False for d in dvpns}
        self.data_caps = {d: 0 for d in dvpns}
        self.CC = {d: 0 for d in dvpns}
        self.LC = {d: 0 for d in dvpns}
        self.prices = {d: 0 for d in dvpns}
        self.unit_prices = {d: 0 for d in dvpns}
        self.last_income = {d: 0 for d in dvpns}

        self.bandwidth_decision = {d: 0 for d in dvpns}
        self.price_decision = {d: 0 for d in dvpns}

        self.t_now = 0
        self.t_month_start = 0
        self.t_next_month = 0

        self.data_cap_adjust = 0.1
        self.needs_diff_thres = 10 # 10GB

        # self.thresholds = {d: 0.5 for d in dvpns}

    def reset(self, dvpn):
        print('Policy.reset', dvpn)
        self.CC[dvpn] = 0
    
    def increase_price(self, dvpn):
        print('Policy.increase_price', dvpn)
        if dvpn == 'mysterium':
            if self.prices[dvpn] < 0.99: # MAX is 1.0
                self.price_decision[dvpn] = self.prices[dvpn] + 0.01
        elif dvpn == 'sentinel':
            if self.prices[dvpn] < 99: # MAX is 100
                self.price_decision[dvpn] = self.prices[dvpn] + 1
        elif dvpn == 'tachyon':
            if self.prices[dvpn] < 0.99: # MAX is 100
                self.price_decision[dvpn] = self.prices[dvpn] + 0.01

    def decrease_price(self, dvpn):
        print('Policy.decrease_price', dvpn)
        if dvpn == 'mysterium':
            if self.prices[dvpn] > 0.01: # MIN is 0.01
                self.price_decision[dvpn] = self.prices[dvpn] - 0.01
        elif dvpn == 'sentinel':
            if self.prices[dvpn] > 1: # MIN is 1
                self.price_decision[dvpn] = self.prices[dvpn] - 1
        elif dvpn == 'tachyon':
            if self.prices[dvpn] > 0.01: # MIN is 0.5
                self.price_decision[dvpn] = self.prices[dvpn] - 0.01
    
    def record(self, dvpn, now, month_start, next_month, 
               data_plan, used_data, 
               curr_bandwidth_limit, bandwidth_history,
               current_price, prices_in_network, unit_price):
        """
        The policy

        Parameters
        ----------
        now : float
            Current timestamp (in seconds).
        month_start : float
            The timestamp at the beginning of the current month (in seconds).
        next_month : float
            The timestamp at the beginning of next month (in seconds).
        data_plan : float
            The data cap for the current month (in bytes).
        used_data : float
            The data have used in the current month (in bytes).
        curr_bandwidth_limit : float
            The current bandwidth limit (in Mbps)
        bandwidth_history : list [{'time': float, 'Bps': float}]
            The used bandwidth for the past N minues, N is the length of the list
        current_price : float
            The current service price
        prices_in_network : json
            The service prices of other dVPN nodes in the network
            Note: sometimes the field "price_per_min" is not present
            [{"account_addr": str, "location": {"country": "US"}, "price_per_GB": float, "price_per_min": float, ...}, ...]
        """

        print('Policy.record', dvpn, now, self.t_next_month)
        self.t_now = now
        if self.t_now > self.t_next_month:
            self.reset(dvpn)
        self.t_month_start = month_start
        self.t_next_month = next_month

        self.ready[dvpn] = True
        self.data_caps[dvpn] = data_plan
        self.LC[dvpn] = 60.0 * sum([bh['Bps'] for bh in bandwidth_history]) / (10**9)
        self.CC[dvpn] += self.LC[dvpn]
        self.prices[dvpn] = current_price
        self.unit_prices[dvpn] = unit_price
        self.last_income[dvpn] = self.LC[dvpn] * self.unit_prices[dvpn]

        self.price_decision[dvpn] = current_price
        self.bandwidth_decision[dvpn] = curr_bandwidth_limit

        # if all the dvpns are updated, then make a decision
        decision_made = True
        for d in self.dvpns:
            decision_made &= self.ready[d]
        if decision_made:
            self.make_decision()

    def make_decision(self):
        print('Policy.make_decision')
        total_last_income = sum([self.last_income[dvpn] for dvpn in self.last_income if self.last_income[dvpn] > 0])
        total_data_cap = sum([self.data_caps[dvpn] for dvpn in self.data_caps if self.last_income[dvpn] > 0])
        # total_last_income = sum(self.last_income.values())
        # total_data_cap = sum(self.data_caps.values())
        time_left = self.t_next_month - self.t_now
        for dvpn in self.dvpns:
            self.ready[dvpn] = False
            if self.last_income[dvpn] <= 0:
                continue

            # adjust data cap
            self.data_caps[dvpn] += self.data_cap_adjust * (total_data_cap * self.last_income[dvpn] / total_last_income - self.data_caps[dvpn])
            self.dvpns[dvpn].update_config({'data-plan': self.data_caps[dvpn]})

            # adjust price setting
            bdw_need = self.LC[dvpn] * time_left
            diff = bdw_need + self.CC[dvpn] - self.LC[dvpn] - self.data_caps[dvpn]
            if diff > self.needs_diff_thres:
                #self.price_decision[dvpn] = self.prices[dvpn] * 1.1
                self.increase_price(dvpn)
                self.dvpns[dvpn].update_config({
                    'price-setting': self.price_decision[dvpn],
                    'bandwidth-limit': self.bandwidth_decision[dvpn]
                })
            elif diff < -self.needs_diff_thres:
                #self.price_decision[dvpn] = self.prices[dvpn] * 0.9
                self.decrease_price(dvpn)
                self.dvpns[dvpn].update_config({
                    'price-setting': self.price_decision[dvpn],
                    'bandwidth-limit': self.bandwidth_decision[dvpn]
                })

        self.save_change()

    def save_change(self):
        print('Policy.save_change')
        result = {}
        result['t_now'] = self.t_now
        result['t_month_start'] = self.t_month_start
        result['t_next_month'] = self.t_next_month
        for dvpn in self.dvpns:
            result[dvpn] = {}
            result[dvpn]['data_cap'] = self.data_caps[dvpn]
            result[dvpn]['CC'] = self.CC[dvpn]
            result[dvpn]['LC'] = self.LC[dvpn]
            result[dvpn]['prices'] = self.prices[dvpn]
            result[dvpn]['unit_prices'] = self.unit_prices[dvpn]
            result[dvpn]['last_income'] = self.last_income[dvpn]
            result[dvpn]['bandwidth_decision'] = self.bandwidth_decision[dvpn]
            result[dvpn]['price_decision'] = self.price_decision[dvpn]

        print(result)
        with open(os.path.join(self.path, "config", 'default_result.json'), 'a+') as fp:
            json.dump(result, fp)
            fp.write('\n')