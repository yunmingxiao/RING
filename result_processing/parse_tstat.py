import json
import os
from datetime import datetime
import time
import Constants #dvpn.result_processing.Constants
import get_labels #dvpn.result_processing.get_labels
from IPy import IP

TIME_LARGE = float('inf')
TIME_WINDOW_ALLOW = 2.00
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

def get_vpn_conns(reqs):
    # return vpn_conns: [{'c_ip': 'x.x.x.x', 'conns': [reqs], 'conn_count': x, 'len_data': (in, out), 'timestamp': [start, end]}]
    # NEW! remove key 'conns'
    # the first vpn_conn is for all
    print('get_vpn_conns begin', len(reqs))
    vpn_conns = [{'c_ip': '0.0.0.0', 'conns': [], 'conn_count': 0, 'len_data': [0, 0], 'timestamp': [TIME_LARGE, 0], 'videos': []}]
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
            for vconn in vpn_conns:
                if (req['conn'][0] == vconn['c_ip'] and is_same_udp_stream(req['timestamp'], vconn['timestamp'])) or (vconn['c_ip'] == '0.0.0.0'):
                    #vconn['conns'].append(req)
                    vconn['conn_count'] += 1
                    vconn['len_data'][0] += req['len_data'][0]
                    vconn['len_data'][1] += req['len_data'][1]
                    vconn['timestamp'][0] = min(req['timestamp'][0], vconn['timestamp'][0])
                    vconn['timestamp'][1] = max(req['timestamp'][1], vconn['timestamp'][1])
                    if vconn['c_ip'] != '0.0.0.0': 
                        flag = True
                        break
            
            if (flag is False) and (not empty_vpn_req2(req)):
                vc = {
                    'c_ip': req['conn'][0],
                    #'conns': [req],
                    'conn_count': 1,
                    'len_data': [req['len_data'][0], req['len_data'][1]],
                    'timestamp': [req['timestamp'][0], req['timestamp'][1]],
                    'videos': []
                }
                if req['conn'][0] == '172.19.0.2':
                    print(req)
                vpn_conns.append(vc)

    print('get_vpn_conns finish', len(vpn_conns))
    return vpn_conns


def match_pkt(vconn, req):
    # if vconn['c_ip'] == "0.0.0.0":
    #     return True

    conn_type = req['conn_type']
    if (req['timestamp'][0] >= vconn['timestamp'][0] - TIME_WINDOW_ALLOW and req['timestamp'][1] <= vconn['timestamp'][1] + TIME_WINDOW_ALLOW):
    # if (req['timestamp'][0] >= vconn['timestamp'][0] and req['timestamp'][1] <= vconn['timestamp'][1]):
        if conn_type == 'udp' or conn_type == 'tcp':
            tcp_data = vconn['data_counter'].get('tcp', [0, 0])
            udp_data = vconn['data_counter'].get('udp', [0, 0])
            if (
                tcp_data[0] + udp_data[0] <= vconn['len_data'][0] * VOLUME_ALLOW - (req['len_data'][0] + req['len_header'][0])
                and tcp_data[1] + udp_data[1] <= vconn['len_data'][1] * VOLUME_ALLOW - (req['len_data'][1] + req['len_header'][1])
            ):
                return True
        elif conn_type == 'p2p':
            if req['conn'][2] in vconn['dst']:
                return True
        else:
            return True

    return False


def add_pkt(vconn, req):
    conn_type = req['conn_type']
    vconn['type_counter'][conn_type] = vconn['type_counter'].get(req['conn_type'], 0) + 1

    vconn['data_counter'][conn_type] = vconn['data_counter'].get(req['conn_type'], [0, 0])
    vconn['data_counter'][conn_type][0] += req['len_data'][0]
    vconn['data_counter'][conn_type][1] += req['len_data'][1]

    vconn['duration_count'][conn_type] = vconn['duration_count'].get(req['conn_type'], [float('inf'), 0])
    vconn['duration_count'][conn_type][0] = min(vconn['duration_count'][req['conn_type']][0], req['timestamp'][0])
    vconn['duration_count'][conn_type][1] = max(vconn['duration_count'][req['conn_type']][1], req['timestamp'][1])
                
    #req['tags'] += get_labels.more_labels(req['dst_url']) # FIXME: temporarily handling, should move this to get_reqs
    if req['dst_url'] and req['dst_url'] != '-':
        vconn['dst'][ req['dst_url'] ] = req['tags'] 
    #else:
    vconn['dst'][ req['conn'][2] ] = req['tags'] 

    for tag in req['tags']:
        vconn['type_counter'][tag] = vconn['type_counter'].get(tag, 0) + 1
        vconn['data_counter'][tag] = vconn['data_counter'].get(tag, [0, 0])
        vconn['data_counter'][tag][0] += req['len_data'][0] + req['len_header'][0]
        vconn['data_counter'][tag][1] += req['len_data'][1] + req['len_header'][1]
        vconn['duration_count'][tag] = vconn['duration_count'].get(tag, [float('inf'), 0])
        vconn['duration_count'][tag][0] = min(vconn['duration_count'][tag][0], req['timestamp'][0])
        vconn['duration_count'][tag][1] = max(vconn['duration_count'][tag][1], req['timestamp'][1])
                
    if req['video']:
        vconn['videos'].append(req['video'])


def match_vpn_conns(reqs, vpn_conns):
    print('match_vpn_conns', len(reqs), len(vpn_conns))
    count, count_matched = {k: 0 for k in Constants.TRAFFIC_TYPES}, {k: 0 for k in Constants.TRAFFIC_TYPES}

    vconn = vpn_conns[0]
    vconn['type_counter'] = vconn.get('type_counter', {})#{k: 0 for k in Constants.TRAFFIC_TYPES})
    vconn['data_counter'] = vconn.get('data_counter', {})#{k: [0, 0] for k in Constants.TRAFFIC_TYPES})
    vconn['duration_count'] = vconn.get('duration_count', {})
    vconn['dst'] = vconn.get('dst', {})

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

        flag = False # if this req is matched
        for index in range(1, len(vpn_conns)):
        #for vconn in vpn_conns[1:]:
            vconn = vpn_conns[index]
            vconn['type_counter'] = vconn.get('type_counter', {})#{k: 0 for k in Constants.TRAFFIC_TYPES})
            vconn['data_counter'] = vconn.get('data_counter', {})#{k: [0, 0] for k in Constants.TRAFFIC_TYPES})
            vconn['duration_count'] = vconn.get('duration_count', {})
            vconn['dst'] = vconn.get('dst', {})

            if match_pkt(vconn, req):
                add_pkt(vconn, req)
                if index != len(vpn_conns) - 1:
                    vpn_conns[index], vpn_conns[index+1] = vpn_conns[index+1], vpn_conns[index]
                # vpn_conns[index], vpn_conns[-1] = vpn_conns[-1], vpn_conns[index]
                add_pkt(vpn_conns[0], req) # vpn_conns is used to calculate the total numbers
                flag = True
                # if index != 0:
                break # when two vpn connections are overlap, consider the outgoing traffic belong to the first vpn connection to avoid repeating count
        
        if flag is True:
            count_matched[req['conn_type']] += 1

    print(count, count_matched)
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

'''
if __name__ == "__main__":
    for vpn in Constants.DVPNs:
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

            vpn_conns = get_vpn_conns(reqs)
            vpn_conns = match_vpn_conns(reqs, vpn_conns)
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
    #for vpn in Constants.DVPNs:
    for vpn in ['sentinel']:#['myst']:
        #for node in Constants.NODES:
        for node in ['aws-us']:#['home']:
            print('main', vpn, node)
            '''
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
            #'''
            reqs = json.load(open('%s/jsons/requests_%s_%s.json' % (Constants.TARGET_DIR, node, vpn), 'r'))
            vpn_conns = get_vpn_conns(reqs)
            vpn_conns = match_vpn_conns(reqs, vpn_conns)
            json.dump(vpn_conns, open('%s/jsons/vpn_conns_%s_%s.json' % (Constants.TARGET_DIR, node, vpn), 'w'))

            #test(reqs, vpn_conns)
            #break
        #break
            #reqs = get_reqs(dirs)
            #reqs = get_tags(reqs)
            #with open('%s/jsons/%s.json' % (Constants.TARGET_DIR, k), 'w') as fp:
            #    json.dump(reqs, fp)
#'''