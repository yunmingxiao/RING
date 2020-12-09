import sys
import os
import subprocess
import copy
import hashlib
import hmac
import re
import json
import time
import datetime
# import sched
from threading import Timer

import iptc
from helpers import controller2web
from generate_ipset import IPSet

def bytes2str(s):
    if type(s) is bytes:
        return s.decode('utf8')
    else:
        print('This is %s not bytes. Convesion Error!' % str(type(s)))
        return ''


class Ifconfig():
    def __init__(self, interfaces={}):
        self.interfaces = interfaces
        self.update_configs()
        self.history = []
        # {'net-myst': {'receive-bytes': 123, 'receive-errs': 123, 'receive-drop': 123, 'transmit-bytes': 123, ...}, ...}
        
    def __str__(self):
        return str(self.interfaces)

    def __getitem__(self, key):
        return self.interfaces[key]

    def keys(self):
        return self.interfaces.keys()

    def add_history(self, ts):
        res = {}
        for i in self.interfaces:
            if self.interfaces[i]:
                res[i] = {
                    "time": ts,
                    "bytes": int(self.interfaces[i]['receive-bytes']) + int(self.interfaces[i]['transmit-bytes']),
                }
        self.history.append(res)
        if len(self.history) > 11:
            self.history.pop(0)

    def update_configs(self, update=True):
        try:
            fp = open('/proc/net/dev', 'r')
            fp.readline() # ignore the first line
            
            headers = fp.readline()
            headers = re.findall(r"[\w'-]+", headers)
            for i in range(1, len(headers)):
                if i <= ( len(headers) / 2 ):
                    headers[i] = 'receive-' + headers[i]
                else:
                    headers[i] = 'transmit-' + headers[i]

            for line in fp:
                values = re.findall(r"[\w'-]+", line)
                dicts = {headers[i]: values[i] for i in range(len(headers))}
                if dicts['face'] in self.interfaces:
                    self.interfaces[ dicts['face'] ] = dicts
            if update:
                self.add_history(time.time())

            return True
        except Exception as e:
            print('Ifconfig.get_configs failed!', e)
            return False

    def get_configs(self, update=True):
        self.update_configs(update)
        return self.interfaces

    def get_history(self):
        ret = {}
        for i in self.interfaces:
            face = i.replace('net-', '')
            if self.interfaces[i]:
                ret[face] = []
                for h in range(1, len(self.history)):
                    ret[face].append({
                        'time': int(self.history[h][i]['time'] * 1000),
                        'bps': (self.history[h][i]['bytes'] - self.history[h-1][i]['bytes']) / (self.history[h][i]['time'] - self.history[h-1][i]['time']),
                    })
        return ret



class TrafficControl():
    def __init__(self, interfaces=[]):
        self.interfaces = interfaces
        self.rules = {}

    def add_rule(self, interface, direction='outgoing', rate_limit=None, delay=None, pkt_loss=None, target_IP=None, ipv6=False):
        # rate_limit: bps, delay: seconds, pkt_loss: %
        cmds = ['tcset', interface, '--change']
        cmds.extend(['--direction', direction])
        if rate_limit:
            cmds.extend(['--rate', '%dbps' % (int(rate_limit))])
        if delay:
            cmds.extend(['--delay', '%dsec' % (int(delay))])
        if pkt_loss:
            cmds.extend(['--loss', '%f\%' % (float(pkt_loss))])
        if target_IP:
            cmds.extend(['--network', target_IP])
        if ipv6:
            cmds.extend(['--ipv6'])

        print('Excute:', ' '.join(cmds))
        p = subprocess.Popen(cmds, stdout=subprocess.PIPE)
        ans = bytes2str(p.communicate()[0])
        p.kill()
        if ans:
            print('TrafficControl.add_rule failed!', ans, cmds)
            return False
        else:
            return True

        #p = subprocess.Popen([
        #    'tcset', 'tc', 'qdisc', 'add', 'dev', self.net_interface, 'root', 'tbf',
        #    'rate', self.bandwidth_thres, 'buffer', '1600', 'limit', '3000'
        #], stdout=subprocess.PIPE)

    def delete_rule(self, interface, target_IP=None, ipv6=False, filter_id=None):
        cmds = ['tcdel', interface]
        if target_IP:
            cmds.extend(['--dst-network', target_IP])
            if ipv6:
                cmds.extend(['--ipv6'])
        elif filter_id:
            cmds.extend(['--id', filter_id])
        else:
            cmds.extend(['--all'])

        print('Excute:', ' '.join(cmds))
        p = subprocess.Popen(cmds, stdout=subprocess.PIPE)
        ans = bytes2str(p.communicate()[0])
        p.kill()
        if ans:
            print('TrafficControl.delete_rule failed!', ans, cmds)
            return False
        else:
            return True

    def update_rules(self):
        for intf in self.interfaces:
            try:
                p = subprocess.Popen(['tcshow', intf], stdout=subprocess.PIPE)
                ans = bytes2str(p.communicate()[0])
                p.kill()
                ans = json.loads(ans)
                print(ans)
                self.rules[intf] = ans[intf]
            except Exception as e:
                print('TrafficControl.update_rules failed!', e, intf) 

        #p = subprocess.Popen(['tc', 'qdisc', 'show'], stdout=subprocess.PIPE)

    def get_rules(self, update=True):
        if update:
            self.update_rules()
        return self.rules


class DVPN():
    def __init__(self, name, configs, path, netlogger):
        self.name = name
        self.net_interface = 'net-' + name
        self.eth_address = configs['eth-address']
        self.data_plan = configs['data-plan']
        self.bandwidth_limit = configs['bandwidth-limit']
        self.auto_bandwidth = configs['auto-bandwidth']
        self.price_setting = configs['price-setting']
        self.auto_price = configs['auto-price']

        self.status = "Inactive"
        self.update_status()
        self.tc = TrafficControl([self.net_interface])

        self.path = path
        self.netlogger = netlogger
        self.used = 0
        self.last_netlog_time = 0
        self.update_used()

    # status
    def update_status(self):
        cmds1 = ['docker', 'container', 'ls', '-a']
        cmds2 = ['grep', self.name]
        print(cmds1, cmds2)
        p1 = subprocess.Popen(cmds1, stdout=subprocess.PIPE)
        p2 = subprocess.Popen(cmds2, stdin=p1.stdout, stdout=subprocess.PIPE)
        ans = bytes2str(p2.communicate()[0])
        p1.kill()
        p2.kill()
        if ans:
            self.status = "Running"
        else:
            self.status = "Inactive"

    def get_status(self):
        self.update_status()
        self.update_used()
        return self.status

    def start(self):
        wd = os.getcwd()
        os.chdir(self.path)
        cmds = ['/bin/bash', 'subscripts/run_dvpn.sh', self.name]
        print(os.getcwd(), cmds)
        p = subprocess.Popen(cmds, stdout=subprocess.PIPE)
        ans = bytes2str(p.communicate()[0])
        print(ans)
        p.kill()
        os.chdir(wd)

    def terminate(self):
        wd = os.getcwd()
        os.chdir(self.path)
        cmds = ['/bin/bash', 'subscripts/stop_dvpn.sh', self.name]
        print(os.getcwd(), cmds)
        p = subprocess.Popen(cmds, stdout=subprocess.PIPE)
        ans = bytes2str(p.communicate()[0])
        print(ans)
        p.kill()
        os.chdir(wd)

    # configures
    def update_used(self):
        todayDate = datetime.date.today()
        month_start = time.mktime(todayDate.replace(day=1).timetuple())
        last_used = 0
        with open(os.path.join(self.netlogger), "r+") as fp:
            for line in fp:
                try:
                    his = json.loads(line)
                    if (last_used == 0) or (his['time'] <= month_start):
                        last_used = float(his['stats'][self.net_interface]["receive-bytes"]) + float(his['stats'][self.net_interface]["transmit-bytes"])
                        last_netlog_time = float(his['time'])
                except:
                    print('failed to read net log:', line)
                    pass
        self.used = last_used
        self.last_netlog_time = last_netlog_time

        if (self.data_plan * 1000000000 <= self.used) and (self.status == "Running"):
            print('used exceeds data plan', self.data_plan * 1000000000, self.used)
            self.terminate()

    def generate_config(self):
        self.update_used()
        configs = {}
        configs['eth-address'] = self.eth_address
        configs['data-plan'] = self.data_plan
        configs['bandwidth-limit'] = self.bandwidth_limit
        configs['auto-bandwidth'] = self.auto_bandwidth
        configs['price-setting'] = self.price_setting
        configs['auto-price'] = self.auto_price
        configs['used-data'] = self.used
        return configs

    def update_config(self, configs, force=False):
        update = False
        for key in configs:
            if key != 'eth-address':
                configs[key] = float(configs[key])

        if force or (self.eth_address != configs['eth-address']):
            self.update_eth_address(configs['eth-address'])
            self.eth_address = configs['eth-address']
            update = True
        if force or (self.data_plan != configs['data-plan']):
            self.update_data_plan(configs['data-plan'])
            self.data_plan = configs['data-plan']
            update = True
        if force or (self.bandwidth_limit != configs['bandwidth-limit']):
            self.bandwidth_limit = configs['bandwidth-limit']
            self.update_bandwidth_limit()
            update = True
        if force or (self.auto_bandwidth != configs['auto-bandwidth']):
            self.auto_bandwidth = configs['auto-bandwidth']
            self.update_auto_bandwidth()
            update = True
        if force or (self.price_setting != configs['price-setting']):
            self.update_price_setting(configs['price-setting'])
            self.price_setting = configs['price-setting']
            update = True
        if force or (self.auto_price != configs['auto-price']):
            self.update_auto_price(configs['auto-price'])
            self.auto_price = configs['auto-price']
            update = True
        return update
        
    def update_eth_address(self, address):
        wd = os.getcwd()
        os.chdir(self.path)
        cmds = ['/bin/bash', 'subscripts/update_eth.sh', self.name, address]
        print(os.getcwd(), cmds)
        p = subprocess.Popen(cmds, stdout=subprocess.PIPE)
        ans = bytes2str(p.communicate()[0])
        print(ans)
        p.kill()
        os.chdir(wd)    
        self.eth_address = address

    def update_data_plan(self, plan):
        pass

    def update_bandwidth_limit(self):
        self.tc.add_rule(self.net_interface, direction='outgoing', rate_limit=self.bandwidth_limit*1000000.0)
        self.tc.add_rule(self.net_interface, direction='incoming', rate_limit=self.bandwidth_limit*1000000.0)

    def update_auto_bandwidth(self):
        if self.auto_bandwidth:
            todayDate = datetime.date.today()
            nextMonthDate = todayDate.replace(day=1).replace(month=todayDate.month%12+1)
            if nextMonthDate.month == 1:
                nextMonthDate = nextMonthDate.replace(year=todayDate.year+1)
            next_month = time.mktime(nextMonthDate.timetuple())
            now = time.time()
            bandwidth_left = 3 * (self.data_plan * 1000000000 - self.used) / (next_month - now) / 1000000.0
            self.bandwidth_limit = bandwidth_left
            self.update_bandwidth_limit()

    def update_price_setting(self, price_setting):
        wd = os.getcwd()
        os.chdir(self.path)
        cmds = ['/bin/bash', 'subscripts/update_price.sh', self.name, str(price_setting)]
        print(os.getcwd(), cmds)
        p = subprocess.Popen(cmds, stdout=subprocess.PIPE)
        ans = bytes2str(p.communicate()[0])
        print(ans)
        p.kill()
        os.chdir(wd)    
        self.price_setting = price_setting

    def update_auto_price(self, auto_price):
        pass


class IPTableManager():
    def __init__(self, ipsets=[], p2p=set([])):
        self.ipsets = ipsets
        self.p2p = p2p

    def modify_p2p_rules(self, new_p2p_rules):
        print('modify_p2p_rules', self.p2p, new_p2p_rules)
        if new_p2p_rules == self.p2p:
            return False

        cmds = ['iptables', '-D', 'FORWARD', '-m', 'ipp2p']
        for p in self.p2p:
            cmds.append('--%s' % (p))
        cmds.extend(['-j', 'DROP'])
        print(cmds)
        p = subprocess.Popen(cmds, stdout=subprocess.PIPE)
        ans = bytes2str(p.communicate()[0])
        p.kill()
        if ans:
            print('IPTableManager.modify_p2p_rules failed!', ans, cmds)

        if len(new_p2p_rules) != 0:
            self.p2p = new_p2p_rules
            # cmds = ['iptables', '-I', 'FORWARD', '-m', 'ipp2p']
            # for p in self.p2p:
            #     cmds.append('--%s' % (p))
            # cmds.extend(['-j', 'DROP'])
            cmds = 'iptables -C FORWARD -m ipp2p'
            for p in self.p2p:
                cmds += ' --%s' % (p)
            cmds += ' -j DROP'
            cmds += ' || iptables -I FORWARD -m ipp2p'
            for p in self.p2p:
                cmds += ' --%s' % (p)
            cmds += ' -j DROP'
            print(cmds)
            p = subprocess.Popen(cmds, stdout=subprocess.PIPE, shell=True)
            ans = bytes2str(p.communicate()[0])
            p.kill()
            if ans:
                print('IPTableManager.modify_p2p_rules failed!', ans, cmds)
        return True

    def activate_ipset(self, ipset):
        # cmds = ['iptables', '-I', 'FORWARD', '-m', 'set', '--match-set', "%s" % (ipset), 'src', '-j', 'DROP'] 
        cmds = 'iptables -C FORWARD -m set --match-set "%s" src -j DROP || iptables -I FORWARD -m set --match-set "%s" src -j DROP' % (ipset, ipset)
        print(cmds)
        p = subprocess.Popen(cmds, stdout=subprocess.PIPE, shell=True)
        ans = bytes2str(p.communicate()[0])
        print(ans)
        p.kill()
    
    def deactivate_ipset(self, ipset):
        cmds = ['iptables', '-D', 'FORWARD', '-m', 'set', '--match-set', "%s" % (ipset), 'src', '-j', 'DROP']
        print(cmds)
        p = subprocess.Popen(cmds, stdout=subprocess.PIPE)
        ans = bytes2str(p.communicate()[0])
        print(ans)
        p.kill()

    def update_ipset(self, new_ipsets):
        update = False
        for ipset in self.ipsets:
            if ipset not in new_ipsets:
                self.deactivate_ipset(ipset)
                update = True
        for ipset in new_ipsets:
            if ipset not in self.ipsets:
                self.activate_ipset(ipset)
                update = True
        self.ipsets = new_ipsets
        return update

    def flush(self):
        cmds = ['iptables', '-F', 'FORWARD'] 
        print(cmds)
        p = subprocess.Popen(cmds, stdout=subprocess.PIPE)
        p.kill()


class Controller():
    def __init__(self, path):
        # common
        self.path = path
        self.op_logger = os.path.join(path, "config", "operation.log")
        self.log_operation("Controller.init: Controller booted")

        # access control
        self.access_rules = {}
        self.iptables = IPTableManager()
        self.ipset_manager = IPSet(path)
        self.load_ipsets()

        # dvpns
        self.dvpn_config = {}
        self.dvpns = {}

        # get last config
        default_flag = False
        try:
            with open(os.path.join(path, "config", "last.conf"), "r") as fp:
                conf = json.load(fp)
                self.access_rules = conf["access_rules"]
                self.dvpn_config = conf["dvpns"]
                self.log_operation("Controller.init: Success reading last config")
                print("Controller.init: Success reading last config", self.dvpn_config)
        except Exception as e:
            self.default_config()
            default_flag = True
            print("Controller.init failed", e)
            self.log_operation("Controller.init: Failed reading last config. Start from default configurations")

        # set up access rules following the last configuration
        # self.iptables.flush()
        self.update_access(self.access_rules, log=False)

        # netstat
        self.stat_logger = os.path.join(path, "config", "netstat.log")
        self.netstat = Ifconfig({'net-' + dvpn: {} for dvpn in self.dvpn_config})
        # cmds = ['mv', self.stat_logger, os.path.join(path, "config", "netstat.log.old")] 
        # print(cmds)
        # p = subprocess.Popen(cmds, stdout=subprocess.PIPE)
        # p.kill()
        self.write_interval = 30 # write every 30 minutes
        self.log_netstat(0, 60) # collect every minute

        # set up dvpn rules following the last configuration
        for dvpn in self.dvpn_config:
            self.dvpns[dvpn] = DVPN(dvpn, self.dvpn_config[dvpn], self.path, self.stat_logger)
            if default_flag:
                self.update_vpn(dvpn, self.dvpn_config[dvpn], force=True)
        self.save()
        print("Controller init finished", self.dvpn_config, self.dvpns)

    # basic operations  
    def save(self):
        conf = {}
        conf['access_rules'] = self.access_rules
        conf['dvpns'] = {dvpn: self.dvpns[dvpn].generate_config() for dvpn in self.dvpns}
        with open(os.path.join(self.path, "config", "last.conf"), "w") as fp:
            json.dump(conf, fp)

    def __del__(self):
        self.save()
        self.update_access(self.access_rules, log=False)
        for dvpn in self.dvpns:
            self.update_vpn(dvpn, {})
          
    def log_operation(self, op):
        with open(os.path.join(self.op_logger), "a+") as fp:
            fp.write(str(time.time()) + " " + str(op) + "\n")

    def log_netstat(self, w, t):
        net_stats = self.netstat.get_configs()
        net_stats = {'time': time.time(), 'stats': net_stats}
        if w == 0:
            # reduce the frequency of writing net log
            w = self.write_interval
            with open(os.path.join(self.stat_logger), "a+") as fp:
                fp.write(str(json.dumps(net_stats)) + "\n")

            # check if the data usage is too much
            for dvpn in self.dvpns:
                self.dvpns[dvpn].update_used()
                self.dvpns[dvpn].update_auto_bandwidth()

        t = Timer(t, self.log_netstat, (w-1, t,))
        t.start()

    def load_ipsets(self):
        for filename in os.listdir(os.path.join(self.path, "config")):
            if '.ipset' in filename:
                ipset_name = filename.replace('.ipset', '')
                print(filename, ipset_name)
                if not self.ipset_manager.check_ipset(ipset_name):
                    print('restore', filename)
                    self.ipset_manager.restore(os.path.join(self.path, "config", filename))

    # index page
    def update_access(self, access_rules, log=True):
        update = False
        print("update_access", self.access_rules, access_rules)
        self.access_rules = access_rules
        p2p = [ar for ar in self.access_rules['p2p'] if self.access_rules['p2p'][ar] is True]
        update |= self.iptables.modify_p2p_rules(p2p)
        ipsets = [ar for ar in self.access_rules['ipset'] if self.access_rules['ipset'][ar] is True]
        update |= self.iptables.update_ipset(ipsets)
        if update and log:
            self.save()
            self.log_operation('Controller.update_access: ' + str(json.dumps(self.access_rules)))

    def get_access(self):
        return controller2web(self.access_rules)

    def get_history(self):
        return self.netstat.get_history()

    # dvpn page
    # # config
    def update_vpn(self, vpn, configs, force=False, log=True):
        update = self.dvpns[vpn].update_config(configs, force)
        if update and log:
            self.save()
            self.log_operation('Controller.update_vpn: ' + vpn + ' ' + str(json.dumps(self.dvpns[vpn].generate_config())))

    def get_config(self, vpn):
        config = self.dvpns[vpn].generate_config()
        current_net = self.netstat.get_configs(update=False)
        current_used = float(current_net['net-'+vpn]["receive-bytes"]) + float(current_net['net-'+vpn]["transmit-bytes"])
        print('Controller.get_config', current_used, config["used-data"])
        config["used-data"] = current_used - config["used-data"]
        return config

    # # status
    def get_status(self, vpn):
        return self.dvpns[vpn].get_status()

    def start(self, vpn, log=True):
        self.log_operation("Controller.start: " + vpn)
        self.dvpns[vpn].start()
        return self.dvpns[vpn].get_status()

    def terminate(self, vpn, log=True):
        self.log_operation("Controller.terminate: " + vpn)
        self.dvpns[vpn].terminate()
        return self.dvpns[vpn].get_status()
        
    def reboot(self, vpn, log=True):
        self.log_operation("Controller.start: " + vpn)
        self.dvpns[vpn].terminate()
        self.dvpns[vpn].start()
        return self.dvpns[vpn].get_status()


    # default config
    def default_config(self):
        self.access_rules = {
            "p2p": {
                "edk": False, 
                "dc": False, 
                "kazaa": False, 
                "gnu": False, 
                "bit": False, 
                "apple": False, 
                "winmx": False, 
                "soul": False, 
                "ares": False, 
            }, 
            "ipset": {
                "Medium": False, 
                "High": False, 
                "Unverified": False, 
                "Pornography": False, 
                "Potential-Criminal-Activities": False, 
                "Potential-Illegal-Software": False, 
                "Illegal-UK": False, 
                "Malicious-Downloads": False, 
                "Malicious-Sites": False, 
                "Phishing": False, 
                "PUPs": False, 
                "Spam-URLs": False, 
                "Browser-Exploits": False, 
                "P2P-Sharing": False, 
                "Spyware": False,
            }
        }
        self.dvpn_config = {
            'mysterium': {
                "eth-address": "0x6715A816b9ea448767655bbf0D62BABd4EAaCd20", 
                "data-plan": 200,
                "bandwidth-limit": 5,
                "auto-bandwidth": False,
                "price-setting": 0.01,
                "auto-price": False,
            },
            'sentinel': {
                "eth-address": "0x6715A816b9ea448767655bbf0D62BABd4EAaCd20", 
                "data-plan": 200,
                "bandwidth-limit": 5,
                "auto-bandwidth": False,
                "price-setting": 0.01,
                "auto-price": False,
            },
            'tachyon': {
                "eth-address": "0x6715A816b9ea448767655bbf0D62BABd4EAaCd20", 
                "data-plan": 200,
                "bandwidth-limit": 5,
                "auto-bandwidth": False,
                "price-setting": 0.01,
                "auto-price": False,
            },
        }


if __name__ == "__main__":
    #a = Ifconfig()
    #print(a)
    #print(a['net-mysterium'])

    # tc = TrafficControl(['net-mysterium'])
    # print(tc.get_rules())

    # ret = tc.add_rule('net-mysterium', rate_limit=100000)
    # print(ret)
    # print(tc.get_rules())

    # ret = tc.add_rule('net-mysterium', rate_limit=100000, direction='incoming')
    # print(ret)
    # print(tc.get_rules())

    # ret = tc.add_rule('net-mysterium', rate_limit=100000, target_IP='98.222.205.35')
    # print(ret)
    # print(tc.get_rules())

    # ret = tc.delete_rule('net-mysterium', target_IP='98.222.205.35')
    # print(ret)
    # print(tc.get_rules())

    # ipt = IPTableManager()
    # ipt.destroy_ipset()
    # ipt.restore()
    # ipt.block(dst='pornhub.com')
    # ipt.activate_ipset()
    # ipt.save()

    # ipt.deactivate_ipset()
    # ipt.destroy_ipset()
    pass