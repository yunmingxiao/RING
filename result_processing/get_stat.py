import time
import json 
import sys
import hashlib
import operator
import numpy as np

from datetime import datetime
import re
import json

import Constants #dvpn.result_processing.Constants

try:
    from geoip import geoiplite2 as geolite2
except:
    from geoip import geolite2

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as tick
from matplotlib import rcParams
rcParams.update({'figure.autolayout': True})
rcParams.update({'figure.autolayout': True})
rcParams.update({'errorbar.capsize': 2})

# increase font 
font = {'weight' : 'medium',
        'size'   : 16}
matplotlib.rc('font', **font)

TIME_FORMAT = "%m/%d" # "%m/%d/%Y-%H:%M:%S"
MIN, HOUR, DAY = 60, 3600, 86400
def to_dt(t):
    return datetime.fromtimestamp(t).strftime(TIME_FORMAT)

def y_fmt(tick_val, pos):
    if tick_val >= 1000000:
        val = int(tick_val)/1000000
        return '%d M' % int(val)
    elif tick_val >= 1000:
        val = int(tick_val) / 1000
        return '%d k' % int(val)
    else:
        return '%d' % int(tick_val)
    
def x_fmt(tick_val, pos):
    if tick_val >= 1000000:
        val = int(tick_val)/1000000
        return '%d M' % int(val)
    elif tick_val >= 1000:
        val = int(tick_val) / 1000
        return '%d k' % int(val)
    else:
        return '%d' % int(tick_val)


def get_user_country(vpn_conns):
    print('get_user_country')
    country_to_ts = {'null': [], 'All': []}
    i, j = 0, 0
    for conn in vpn_conns:
        #print(type(conn['c_ip']), conn['c_ip'])
        if empty_conn(conn):
            continue
        geo = geolite2.lookup(conn['c_ip'])
        if geo is not None:
            j += 1
            geo = geo.to_dict()
            #print(conn)
            #print('success', j, conn['c_ip'], conn['len_data'])
        else:
            i += 1
            #print('fail', i, conn['c_ip'], conn['len_data'])
            #print(conn)
            geo = {}
        country_to_ts['All'].append(conn['timestamp'][0])
        if 'country' in geo:
            country_to_ts[geo['country']] = country_to_ts.get(geo['country'], [])
            country_to_ts[geo['country']].append(conn['timestamp'][0])
        else:
            country_to_ts['null'].append(conn['timestamp'][0])
    
    country_num = {cu: len(country_to_ts[cu]) for cu in country_to_ts}
    country_num = {k: v for k, v in sorted(country_num.items(), key=lambda item: item[1])}
    print(country_num, len(country_num))
    del country_num['null']
    country_num_top_N = {key: country_num[key] for key in sorted(country_num, key=country_num.get, reverse=True)[:10]}
    print(country_num_top_N)


def empty_conn(vconn):
    if vconn['len_data'][0] + vconn['len_data'][1] < 10*4:
        return True
    if vconn['timestamp'][1] - vconn['timestamp'][0] < 1:
        return True 
    if ('data_counter' not in vconn) or ('type_counter' not in vconn) or ('duration_count' not in vconn):
        return True
    if (
        (('tcp' not in vconn['data_counter']) or (vconn['data_counter']['tcp'][0] + vconn['data_counter']['tcp'][1] < 10*3))
        and (('udp' not in vconn['data_counter']) or (vconn['data_counter']['udp'][0] + vconn['data_counter']['udp'][1] < 10*3))
        ):
        return True
    return False

def get_volume(vpn_conns, node, vpn):
    print('get_volume')
    volumes, bandwidth, duration = {'vpn': []}, {'vpn': []}, {'vpn': []}
    print(vpn_conns[0]['len_data'],  vpn_conns[0]['data_counter'], vpn_conns[0]['timestamp'], vpn_conns[0]['duration_count'], )
    #print(vpn_conns[0]['len_data'], vpn_conns[0]['timestamp'])
    empty_count = 0
    for vconn in vpn_conns[1:]:
        if empty_conn(vconn):
            empty_count += 1
            continue

        volumes['vpn'].append( vconn['len_data'][0] + vconn['len_data'][1] )
        duration['vpn'].append( vconn['timestamp'][1] - vconn['timestamp'][0] ) 
        if duration['vpn'][-1] > 0:
            bandwidth['vpn'].append( volumes['vpn'][-1] / duration['vpn'][-1] )
        else:
            bandwidth['vpn'].append( volumes['vpn'][-1] / (duration['vpn'][-1] + 0.001) )

        tag_set = list( set(['tcp', 'udp', 'p2p']) | set(vconn['type_counter'].keys()) )
        for tag in tag_set:
            volumes[tag] = volumes.get(tag, [])
            duration[tag] = duration.get(tag, [])
            bandwidth[tag] = bandwidth.get(tag, [])

            if tag in vconn['data_counter']:
                volumes[tag].append( vconn['data_counter'][tag][0] + vconn['data_counter'][tag][1] )
            else:
                volumes[tag].append(0)
            if tag in vconn['duration_count']:
                duration[tag].append( vconn['duration_count'][tag][1] - vconn['duration_count'][tag][0] ) 
            else:
                duration[tag].append(0)
            if duration[tag][-1] > 0:
                bandwidth[tag].append( volumes[tag][-1] / duration[tag][-1] )
            else:
                #bandwidth[tag].append( volumes[tag][-1] / (duration[tag][-1] + 0.001) )
                bandwidth[tag].append(0)
    
    print('Number of connection', len(vconn),)# {k: len(v) for k, v in volumes.items()})
    # if sum(volumes['vpn']) == 0:
    #     print('Volumes', sum(volumes['vpn']) / 1000000.0, {k: sum(v) for k, v in volumes.items()})
    # else:
    print(len(vpn_conns), empty_count,)# volumes['vpn'])
    print('Volumes', sum(volumes['vpn']) / 1000000.0, {k: sum(v) / sum(volumes['vpn']) for k, v in volumes.items()})
    print('Duration', np.average(duration['vpn']), {k: np.average(v) for k, v in duration.items()})
    print('Bandwidth', np.average(bandwidth['vpn']), {k: np.average(bandwidth['vpn']) / 1000.0 for k, v in bandwidth.items()})
    print('empty_count', empty_count)

    # volumes CDF
    colors = ['k', 'r', 'g', 'b', 'orange']
    keys = ['vpn', 'tcp', 'udp', 'p2p']
    plt.clf()
    for i in range(4):
        key, color = keys[i], colors[i]
        volumes_cdf = [v / 1000000.0 for v in volumes[key]]
        #volumes_cdf = [v for v in volumes[key]]
        empty_count = sum([1 for vc in volumes_cdf if vc == 0])
        print('Number of empty volume for %s is %d out of %d' % (key, empty_count, len(volumes_cdf)))
        x, y = sorted(volumes_cdf), np.arange(1, 1 + len(volumes_cdf)) / len(volumes_cdf)
        plt.plot(x, y, color=color, linewidth = 2, label=key)
    plt.xlabel("Traffic Volumes (MB)")
    plt.ylabel("CDF")
    plt.grid(True)
    #plt.xlim(0, max(volumes['vpn']))
    plt.xscale('log')
    #plt.xlim(left=0)
    plt.xlim(0.001, 3*10**3)
    plt.ylim(0, 1)
    plt.legend(loc='lower right')
    plt.savefig("%s/figs/cdf_volume_%s_%s.pdf" % (Constants.TARGET_DIR, node, vpn))

    plt.clf()
    for i in range(4):
        key, color = keys[i], colors[i]
        duration_cdf = [v for v in duration[key]]
        x, y = sorted(duration_cdf), np.arange(1, 1 + len(duration_cdf)) / len(duration_cdf)
        plt.plot(x, y, color=color, linewidth = 2, label=key)
    plt.xlabel("Duration (s)")
    plt.ylabel("CDF")
    plt.grid(True)
    plt.xscale('log')
    #plt.xlim(0, max(duration_cdf))
    #plt.xlim(left=0)
    plt.xlim(0.01, 3*10**4)
    plt.ylim(0, 1)
    #plt.show()
    plt.legend(loc='lower right')
    plt.savefig("%s/figs/cdf_duration_%s_%s.pdf" % (Constants.TARGET_DIR, node, vpn))

    plt.clf()
    for i in range(4):
        key, color = keys[i], colors[i]
        bandwidth_cdf = [v / 1000.0 for v in bandwidth[key]]
        x, y = sorted(bandwidth_cdf), np.arange(1, 1 + len(bandwidth_cdf)) / len(bandwidth_cdf)
        plt.plot(x, y, color=color, linewidth = 2, label=key)
    plt.xlabel("Bandwidth (kB/s)")
    plt.ylabel("CDF")
    plt.grid(True)
    plt.xscale('log')
    #plt.xlim(0, max(bandwidth_cdf))
    #plt.xlim(left=0)
    plt.xlim(0.001, 3*10**3)
    plt.ylim(0, 1)
    #plt.show()
    plt.legend(loc='lower right')
    plt.savefig("%s/figs/cdf_bandwidth_%s_%s.pdf" % (Constants.TARGET_DIR, node, vpn))
    

    

if __name__ == "__main__":
    all_vpns = []
    for vpn in Constants.DVPNs:
    # for vpn in ['tachyon']:
        all_vpn_nodes = []
        for node in Constants.NODES:
        # for node in ['aws-us']: #['home']:
            print('\n\nget_stat', vpn, node)
            try:
                vpn_conns = json.load(open('%s/jsons/vpn_conns_%s_%s.json' % (Constants.TARGET_DIR, node, vpn), 'r'))
                get_user_country(vpn_conns)
                get_volume(vpn_conns, node, vpn)
            except Exception as e: 
                print('failed!', e)
                vpn_conns = []
            all_vpn_nodes.extend(vpn_conns)
            print('done', vpn, node, '\n')

        print('\n\nall nodes')
        try:
            get_user_country(all_vpn_nodes)
            get_volume(all_vpn_nodes, 'allnodes', vpn)
        except Exception as e: 
            print('failed!', e)
        all_vpns.extend(all_vpn_nodes)
    
    print('\n\nall vpns')
    get_user_country(all_vpns)
    get_volume(all_vpns, 'allnodes', 'allvpns')