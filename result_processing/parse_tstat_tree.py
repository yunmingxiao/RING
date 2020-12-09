import json
import os
import sys
from datetime import datetime
import time
import Constants #dvpn.result_processing.Constants
import get_labels #dvpn.result_processing.get_labels
from IPy import IP

from intervaltree import Interval, IntervalTree
import random
import gc

TIME_LARGE = float('inf')
TIME_WINDOW_ALLOW = 1.00
VOLUME_ALLOW = 1.1

def get_dirs(parent_dir, node, vpn, key):
    # return list of directories
    subdirs = os.listdir(os.path.join(parent_dir, node, vpn))
    dir_list = []
    for sd in subdirs:
        d = os.path.join(parent_dir, node, vpn, sd)
        if os.path.isdir(d):
            dir_list.append(os.path.join(d, key))
    return dir_list


def get_dirs2(parent_dir, vpn, key):
    # return list of directories
    subdirs = os.listdir(os.path.join(parent_dir, vpn))
    dir_list = []
    for sd in subdirs:
        d = os.path.join(parent_dir, vpn, sd)
        if os.path.isdir(d):
            dir_list.append(os.path.join(d, key))
    return dir_list


def get_reqs(filename):
    # return [{"conn": (ip_src, port_src, ip_dst, port_dst), "conn_type": "http", "timestamp": float or (float, float), "dst_url": "xxx.com", "p2p": , "len_data": (int, int),}, ]
    ret = []
    try:
        with open(filename, 'rb') as fp:
            line = fp.readline().decode('utf-8')
            if line:
                line = line.split('#')[-1]
                columns = [z.split(':') for z in line.split()]
                headers = {z[0]: int(z[1])-1 for z in columns}
                invhead = {int(z[1])-1: z[0] for z in columns}
                for line in fp:
                    try:
                        line = line.decode('utf-8')
                    except:
                        continue
                    if line.startswith('#'):
                        continue
                    conn = line.split()
                    if len(conn) < len(headers):
                        print('Error!', len(conn), len(headers), conn)
                        continue

                    try:
                        conn = {invhead[i]: val for i, val in enumerate(conn)}
                    except:
                        continue
                    
                    if 'log_http_complete' in filename:
                        if conn['method'] == 'HTTP':
                            # ignore the redundant record for now
                            continue

                        ret.append({
                            "conn": (conn['c_ip'], int(conn['c_port']), conn['s_ip'], int(conn['s_port'])),
                            "conn_type": "http",
                            "timestamp": (float(conn['time_abs']), float(conn['time_abs'])),
                            "dst_url": conn['fqdn'],
                            "len_data": (0, 0),
                            "len_header": (0, 0),
                            "p2p": None,
                            "video": None,
                        })

                    elif 'log_tcp_complete' in filename:
                        ret.append({
                            "conn": (conn['c_ip'], int(conn['c_port']), conn['s_ip'], int(conn['s_port'])),
                            "conn_type": "tcp",
                            "timestamp": (float(conn['first']) / 1000., float(conn['last']) / 1000.),
                            "dst_url": conn['fqdn'],
                            "len_data": (int(conn['c_bytes_all']), int(conn['s_bytes_all'])),
                            "len_header": (int(conn['c_pkts_all'])*20, int(conn['c_pkts_all'])*20),
                            "p2p": int(conn['p2p_st']),
                            "video": None,
                        })

                    elif 'log_tcp_nocomplete' in filename:
                        ret.append({
                            "conn": (conn['c_ip'], int(conn['c_port']), conn['s_ip'], int(conn['s_port'])),
                            "conn_type": "tcp",
                            "timestamp": (float(conn['first']) / 1000., float(conn['last']) / 1000.),
                            "dst_url": None,
                            "len_data": (int(conn['c_bytes_all']), int(conn['s_bytes_all'])),
                            "len_header": (int(conn['c_pkts_all'])*20, int(conn['c_pkts_all'])*20),
                            "p2p": None,
                            "video": None,
                        })

                    elif 'log_udp_complete' in filename:
                        p2p = int(conn['c_type'])
                        if (p2p >= 8 and p2p <= 18) or (p2p == 20) or (p2p == 21) or (p2p == 23):
                            pass
                        else:
                            p2p = None
                        ret.append({
                            "conn": (conn['c_ip'], int(conn['c_port']), conn['s_ip'], int(conn['s_port'])),
                            "conn_type": "udp",
                            "timestamp": (
                                float(conn['c_first_abs']) / 1000., 
                                max(
                                    float(conn['c_first_abs']) / 1000. + float(conn['c_durat']), 
                                    float(conn['s_first_abs']) / 1000. + float(conn['s_durat'])
                                )  
                            ),
                            "dst_url": conn['fqdn'],
                            "len_data": (int(conn['c_bytes_all']), int(conn['s_bytes_all'])),
                            "len_header": (int(conn['c_pkts_all'])*8, int(conn['c_pkts_all'])*8),
                            "p2p": p2p,
                            "video": None,
                        })

                    elif 'log_video_complete' in filename:
                        ret.append({
                            "conn": (conn['c_ip'], int(conn['c_port']), conn['s_ip'], int(conn['s_port'])),
                            "conn_type": "tcp",
                            "timestamp": (float(conn['first']) / 1000., float(conn['last']) / 1000.),
                            "dst_url": conn['fqdn'],
                            "len_data": (int(conn['c_bytes_all']), int(conn['s_bytes_all'])),
                            "len_header": (int(conn['c_pkts_all'])*20, int(conn['c_pkts_all'])*20),
                            "p2p": int(conn['p2p_t']),
                            "video": {
                                "type": int(conn['vd_type_cont']),
                                "duration": float(conn['vd_dur']),
                                "rate": float(conn['vd_rate_tot']),
                                "width": int(conn['vd_width']),
                                "height": int(conn['vd_height']),
                            },
                        })

                    else:
                        print('Something wrong?', filename)
    except Exception as e:
        print(e)
    return ret


def get_tags(reqs):
    # return [{"conn": ..., "tags": [p2p, ipban, threat]]
    print('get_tags', len(reqs))
    count = 0
    for req in reqs:
        count += 1
        if count % 50000 == 0:
            print(datetime.fromtimestamp(time.time()), count)

        # ignore the incoming traffic
        #if IP(req['conn'][2]).iptype() != 'PUBLIC':
        #    continue
        # if not is_internal_ip(req['conn'][0]):
        #     req['tags'] = []
        #     continue

        if req['dst_url'] and req['dst_url'] != '-':
            req['tags'] = get_labels.is_suspicious(req['dst_url'], req['p2p'])
        else:
            req['tags'] = get_labels.is_suspicious(req['conn'][2], req['p2p'])

    return reqs


INTER_PCK_TIME = 30 * 60 # seconds
def is_same_udp_stream(t1, t2):
    if t1[0] <= t2[0] and t1[1] >= t2[0] - INTER_PCK_TIME:
        return True
    elif t1[0] >= t2[0] and t1[0] <= t2[1] + INTER_PCK_TIME:
        return True
    else:
        return False

def empty_vpn_req(req):
    if req['conn_type'] != 'tcp':
        return False
    if req['len_data'][0] + req['len_data'][1] < 100:
        return True
    if req['timestamp'][1] - req['timestamp'][0] <= 0:
        return True 
    return False

def empty_vpn_req2(req):
    if req['len_data'][0] + req['len_data'][1] < 10*4:
        return True
    if req['timestamp'][1] - req['timestamp'][0] < 1:
        return True 
    return False

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

def is_internal_ip(ip):
    if (
        (IP(ip).iptype() == 'PRIVATE')
        or (ip in Constants.NODES_IP.values())
        ):
        return True
    return False

class VPNConnection():
    def __init__(self, data):
        self.data = data

    def add_vpn_req(self, req):
        self.data['conn_count'] += 1
        self.data['len_data'][0] += req['len_data'][0]
        self.data['len_data'][1] += req['len_data'][1]
        self.data['timestamp'][0] = min(req['timestamp'][0], self.data['timestamp'][0])
        self.data['timestamp'][1] = max(req['timestamp'][1], self.data['timestamp'][1])

    def match_pkt(self, req):
        if (req['timestamp'][0] >= self.data['timestamp'][0] - TIME_WINDOW_ALLOW and req['timestamp'][1] <= self.data['timestamp'][1] + TIME_WINDOW_ALLOW):
            conn_type = req['conn_type']
            if conn_type == 'udp' or conn_type == 'tcp':
                tcp_data = self.data['data_counter'].get('tcp', [0, 0])
                udp_data = self.data['data_counter'].get('udp', [0, 0])
                if (
                    tcp_data[0] + udp_data[0] <= self.data['len_data'][0] * VOLUME_ALLOW - (req['len_data'][0] + req['len_header'][0])
                    and tcp_data[1] + udp_data[1] <= self.data['len_data'][1] * VOLUME_ALLOW - (req['len_data'][1] + req['len_header'][1])
                ):
                    return True
            elif conn_type == 'p2p':
                if req['conn'][2] in self.data['dst']:
                    return True
            else:
                return True
        return False

    def add_pkt(self, req):
        conn_type = req['conn_type']
        self.data['type_counter'][conn_type] = self.data['type_counter'].get(req['conn_type'], 0) + 1

        self.data['data_counter'][conn_type] = self.data['data_counter'].get(req['conn_type'], [0, 0])
        self.data['data_counter'][conn_type][0] += req['len_data'][0]
        self.data['data_counter'][conn_type][1] += req['len_data'][1]

        self.data['duration_count'][conn_type] = self.data['duration_count'].get(req['conn_type'], [float('inf'), 0])
        self.data['duration_count'][conn_type][0] = min(self.data['duration_count'][req['conn_type']][0], req['timestamp'][0])
        self.data['duration_count'][conn_type][1] = max(self.data['duration_count'][req['conn_type']][1], req['timestamp'][1])
                    
        req['tags'] += get_labels.more_labels(req['dst_url']) # FIXME: temporarily handling, should move this to get_reqs
        if req['dst_url'] and req['dst_url'] != '-':
            self.data['dst'][ req['dst_url'] ] = req['tags'] 
        #else:
        self.data['dst'][ req['conn'][2] ] = req['tags'] 

        for tag in req['tags']:
            self.data['type_counter'][tag] = self.data['type_counter'].get(tag, 0) + 1
            self.data['data_counter'][tag] = self.data['data_counter'].get(tag, [0, 0])
            self.data['data_counter'][tag][0] += req['len_data'][0] + req['len_header'][0]
            self.data['data_counter'][tag][1] += req['len_data'][1] + req['len_header'][1]
            self.data['duration_count'][tag] = self.data['duration_count'].get(tag, [float('inf'), 0])
            self.data['duration_count'][tag][0] = min(self.data['duration_count'][tag][0], req['timestamp'][0])
            self.data['duration_count'][tag][1] = max(self.data['duration_count'][tag][1], req['timestamp'][1])
                    
        if req['video']:
            self.data['videos'].append(req['video'])


def get_vpn_conns(reqs):
    # return vpn_conns: [{'c_ip': 'x.x.x.x', 'conns': [reqs], 'conn_count': x, 'len_data': (in, out), 'timestamp': [start, end]}]
    # NEW! remove key 'conns'
    # the first vpn_conn is for all
    print('get_vpn_conns begin', len(reqs))
    vpn_summary = VPNConnection({'c_ip': '0.0.0.0', 'conns': [], 'conn_count': 0, 'len_data': [0, 0], 'timestamp': [TIME_LARGE, 0], 'videos': []})
    vpn_conns_ipdict = {}
    c = 0
    for req in reqs:
        c += 1
        if c % 50000 == 0:
            print(datetime.fromtimestamp(time.time()), c)
        if ( not is_internal_ip(req['conn'][0])
             and (req['conn_type'] != 'http') 
             and (req['conn'][3] not in Constants.CONTROL_PORTS.values())
             and (not empty_vpn_req(req)) ):
            flag = False # if this req belong to one of the previous vpn connections
            ip_src = req['conn'][0]
            if ip_src in vpn_conns_ipdict:
                for vconn in vpn_conns_ipdict[ip_src]:
                    if is_same_udp_stream(req['timestamp'], vconn.data['timestamp']):
                        vconn.add_vpn_req(req)
                        flag = True
                        vpn_summary.add_vpn_req(req)
                        break
            
            if (flag is False) and (not empty_vpn_req2(req)):
                if ip_src == '172.19.0.2':
                    print(req)
                vc_data = {
                    'c_ip': ip_src,
                    #'conns': [req],
                    'conn_count': 1,
                    'len_data': [req['len_data'][0], req['len_data'][1]],
                    'timestamp': [req['timestamp'][0], req['timestamp'][1]],
                    'videos': []
                }
                vc = VPNConnection(vc_data)
                vpn_conns_ipdict[ip_src] = vpn_conns_ipdict.get(ip_src, [])
                vpn_conns_ipdict[ip_src].append(vc)
                vpn_summary.add_vpn_req(req)

    print('building interval tree')
    vpn_conns_tree = IntervalTree()
    for k, v in vpn_conns_ipdict.items():
        for vv in v:
            vpn_conns_tree[ vv.data['timestamp'][0] : vv.data['timestamp'][1] ] = vv
    print('get_vpn_conns finish', len(vpn_conns_tree))

    return vpn_conns_tree, vpn_summary


def match_vpn_conns(reqs, vpn_conns_tree, vpn_summary):
    print('match_vpn_conns', len(reqs), len(vpn_conns_tree))
    count, count_matched = {k: 0 for k in Constants.TRAFFIC_TYPES}, {k: 0 for k in Constants.TRAFFIC_TYPES}

    vpn_summary.data['type_counter'] = {}#{k: 0 for k in Constants.TRAFFIC_TYPES})
    vpn_summary.data['data_counter'] = {}#{k: [0, 0] for k in Constants.TRAFFIC_TYPES})
    vpn_summary.data['duration_count'] = {}
    vpn_summary.data['dst'] = {}

    c = 0
    for req in reqs:
        c += 1
        if c % 50000 == 0:
            print(datetime.fromtimestamp(time.time()), c)
        # ignore the incoming traffic
        if not is_internal_ip(req['conn'][0]):
            continue

        count[req['conn_type']] += 1
        if sum(count.values()) == 0:
            print(sum(count.values()))

        vconn_options = []
        for vconn_node in vpn_conns_tree[ req['timestamp'][0] - TIME_WINDOW_ALLOW : req['timestamp'][0] + TIME_WINDOW_ALLOW ]:
            vconn = vconn_node.data
            vconn.data['type_counter'] = vconn.data.get('type_counter', {})#{k: 0 for k in Constants.TRAFFIC_TYPES})
            vconn.data['data_counter'] = vconn.data.get('data_counter', {})#{k: [0, 0] for k in Constants.TRAFFIC_TYPES})
            vconn.data['duration_count'] = vconn.data.get('duration_count', {})
            vconn.data['dst'] = vconn.data.get('dst', {})

            if vconn.match_pkt(req):
                vconn_options.append(vconn)
        
        if len(vconn_options) > 0:
            vconn = random.choice(vconn_options)
            vconn.add_pkt(req)
            vpn_summary.add_pkt(req)
            count_matched[req['conn_type']] += 1

    print(count, count_matched)
    print('match_vpn_conns, Making json')
    vpn_conns = [vpn_summary.data]
    for vconn in vpn_conns_tree:
        vpn_conns.append(vconn.data.data)
    print('match_vpn_conns, Done')
    return vpn_conns


def test(reqs, vpn_conns):
    print('test')
    # res_dst_private, res_p2p = [], []
    # for req in reqs:
    #     if IP(req['conn'][2]).iptype() != 'PUBLIC' and req['conn_type'] != 'http' and req['conn'][3] not in Constants.CONTROL_PORTS.values():
    #         res_dst_private.append(req)
    #     if req['p2p']:
    #         res_p2p.append(req)
    # json.dump(res_dst_private, open('test/dst_is_private.json', 'w'))
    # json.dump(res_p2p, open('test/p2p_traffic.json', 'w'))
    # for vconn in vpn_conns:
    #     print(vconn['c_ip'], len(vconn['conns']), vconn['timestamp'][1] - vconn['timestamp'][0], vconn['timestamp'][0], vconn['timestamp'][1], vconn['len_data'], vconn['data_counter'], vconn['type_counter'])
    a = get_reqs('../output/ovh.new/tachyon/2020_08_18_15_43.out/log_http_complete')
    print(a)
    #b = get_reqs('../output/ovh.new/tachyon/2020_07_30_20_03.out/log_tcp_complete')
    #print(b)

#'''
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Error! Usage: python3 parse_tstat_tree.py requests/conns')
    execution = sys.argv[1]
    for vpn in Constants.DVPNs:
        if execution == 'requests':
            reqs = []
            for log_name in Constants.LOG_NAME:
                dirs = get_dirs2(os.path.join(Constants.DVPN_DIR, 'output'), vpn, log_name)
                if len(dirs) > 0:
                    print(dirs[0], len(dirs))
                for filename in dirs:
                    print(filename)
                    temp_reqs = get_reqs(filename)
                    reqs.extend(temp_reqs)
            print(len(reqs))
            #test(reqs)
            reqs = get_tags(reqs)
            json.dump(reqs, open('%s/jsons/requests_%s.json' % (Constants.TARGET_DIR, vpn), 'w'))
        
        elif execution == 'conns':
            reqs = json.load(open('%s/jsons/requests_%s.json' % (Constants.TARGET_DIR, vpn), 'r'))
            vpn_conns_tree, vpn_summary = get_vpn_conns(reqs)
            vpn_conns = match_vpn_conns(reqs, vpn_conns_tree, vpn_summary)
            json.dump(vpn_conns, open('%s/jsons/vpn_conns_%s.json' % (Constants.TARGET_DIR, vpn), 'w'))

        #test(reqs, vpn_conns)
        #break
    #break
        #reqs = get_reqs(dirs)
        #reqs = get_tags(reqs)
        #with open('%s/jsons/%s.json' % (Constants.TARGET_DIR, k), 'w') as fp:
        #    json.dump(reqs, fp)
'''
if __name__ == "__main__":
    # test('1', '2')
    # exit()
    for vpn in Constants.DVPNs:
    # for vpn in ['tachyon']:#['myst']:
        for node in Constants.NODES:
        # for node in ['aws-us']:#['home']:
            print('\n\nmain', vpn, node)
            
            reqs = []
            for log_name in Constants.LOG_NAME:
                dirs = get_dirs(os.path.join(Constants.DVPN_DIR, 'output'), node, vpn, log_name)
                if len(dirs) > 0:
                    print(dirs[0], len(dirs))
                for filename in dirs:
                    print(filename)
                    temp_reqs = get_reqs(filename)
                    reqs.extend(temp_reqs)
            print(len(reqs))
            #test(reqs)
            reqs = get_tags(reqs)
            json.dump(reqs, open('%s/jsons/requests_%s_%s.json' % (Constants.TARGET_DIR, node, vpn), 'w'))
            #
            reqs = json.load(open('%s/jsons/requests_%s_%s.json' % (Constants.TARGET_DIR, node, vpn), 'r'))
            vpn_conns_tree, vpn_summary = get_vpn_conns(reqs)
            vpn_conns = match_vpn_conns(reqs, vpn_conns_tree, vpn_summary)
            json.dump(vpn_conns, open('%s/jsons/vpn_conns_%s_%s.json' % (Constants.TARGET_DIR, node, vpn), 'w'))
            print('done', vpn, node, '\n')

            #test(reqs, vpn_conns)
            #break
        #break
            #reqs = get_reqs(dirs)
            #reqs = get_tags(reqs)
            #with open('%s/jsons/%s.json' % (Constants.TARGET_DIR, k), 'w') as fp:
            #    json.dump(reqs, fp)
#'''