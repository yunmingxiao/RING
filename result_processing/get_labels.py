from gglsbl import SafeBrowsingList
from adblockparser import AdblockRules
from IPy import IP, IPSet
import socket
import requests
import time
import json

from bs4 import BeautifulSoup

import mcafee
import Constants #dvpn.result_processing.Constants

with open('%s/filters/easylist.txt' % (Constants.TARGET_DIR), 'r') as f:
    ad_rules = list()
    for line in f:
        if line.startswith('!'):
            continue
        ad_rules.append(line.strip())
ad_rules = AdblockRules(ad_rules)

def is_ad(url):
    try:
        return ad_rules.should_block(url)
    except:
        return False


with open('%s/filters/easyprivacy.txt' % (Constants.TARGET_DIR), 'r') as f:
    tracker_rules = list()
    for line in f:
        if line.startswith('!'):
            continue
        tracker_rules.append(line.strip())
tracker_rules = AdblockRules(tracker_rules)

def is_tracker(url):
    try:
        return tracker_rules.should_block(url)
    except:
        return False


with open('%s/filters/firehol_level1.netset' % (Constants.TARGET_DIR),'r') as f:
    banned_ips = list()
    for line in f:
        if line.startswith('#'):
            continue
        banned_ips.append(IP(line))

def is_banned_IP(url):
    try:
        ip = IP(socket.gethostbyname(url))
        return ip in banned_ips
    except:
        try:
            ip = IP(url)
            return ip in banned_ips
        except:
            return False


# with open('%s/filters/coin-miners.txt' % (Constants.TARGET_DIR), 'r') as f:
#     miner_rules = list()
#     for line in f:
#         if line.startswith('!'):
#             continue
#         miner_rules.append(line.strip())
# miner_rules = AdblockRules(miner_rules)

# def is_miner(url):
#     try:
#         return miner_rules.should_block(url)
#     except:
#         return False


sbl = SafeBrowsingList(Constants.gsbk, '%s/filters/gsb_v4.db' % (Constants.TARGET_DIR))
def is_threat(url):
    try:
        return [str(z) for z in sbl.lookup_url(url)]
    except:
        return None


def is_suspicious(url, p2p):
    types = list()
    if p2p:
        types.append('p2p')
    #if is_ad(url):
    #    types.append('ad')
    if is_tracker(url):
        types.append('track')
    # if is_threat(url):
    #     types.append('threat')
    #if is_miner(url):
    #    types.append('miner')
    if is_banned_IP(url):
        types.append('ipban')
    return types

# try:
#     opendns_labels = json.load(open("%s/filters/opendns.json" % (Constants.TARGET_DIR), "r"))
# except:
#     opendns_labels = {}
try:
    mcafee_labels = json.load(open("%s/filters/mcafee_category.json" % (Constants.TARGET_DIR), "r"))
except:
    mcafee_labels = {}
try:
    mcafee_security = json.load(open("%s/filters/mcafee_security.json" % (Constants.TARGET_DIR), "r"))
except:
    mcafee_security = {}
def more_labels(url):
    types = list()
    # if url in opendns_labels:
    #     types.extend(opendns_labels[url])
    if url in mcafee_labels:
        types.extend(mcafee_labels[url])
    if url in mcafee_security:
        types.append(mcafee_security[url])
    return types


def parse_opendns(req, label_dict):
    ret = requests.get("https://domain.opendns.com/%s" % (req['dst_url'],))
    soup = BeautifulSoup(ret.text, 'html.parser')
    cells = soup.find(id="maincontent").div.div.table.find_all('tr')
    for c in cells[1:]:
        tds = c.find_all('td')
        if "Approved" in tds[2].text:
            label_dict[req['dst_url']].append(tds[1].b.text.strip())

def parse_mcafee(req, label_dict, security_dict, headers, token1, token2):
    categorized, category, risk = mcafee.lookup(headers, token1, token2, req['dst_url'])
    security_dict[req['dst_url']] = risk
    if categorized == 'Categorized URL':
        label_dict[req['dst_url']].extend(category.split('- '))
        return True
    else:
        return False


def get_label(filename):
    # get label from the OpenDNS
    try:
        label_dict_opendns = json.load(open("%s/filters/opendns.json" % (Constants.TARGET_DIR), "r"))
    except:
        label_dict_opendns = {}
    
    mcafee_headers, mcafee_token1, mcafee_token2 = mcafee.setup()
    try:
        label_dict_mcafee = json.load(open("%s/filters/mcafee_category.json" % (Constants.TARGET_DIR), "r"))
        security_dict_mcafee = json.load(open("%s/filters/mcafee_security.json" % (Constants.TARGET_DIR), "r"))
    except:
        label_dict_mcafee = {}
        security_dict_mcafee = {}

    reqs = json.load(open(filename, 'r'))
    print('total', len(reqs))
    success_opendns, success_mcafee = 0, 0 
    i_opendns, i_mcafee = 0, 0 
    count = 0
    for req in reqs:
        count += 1
        # if count < 210000:
        #     continue
        if count % 1000000 == 0:
            print('count', count)
        if req['dst_url'] is not None:
            if req['dst_url'] not in label_dict_opendns:
                i_opendns += 1
                if i_opendns % 300 == 0:
                    print('OpenDNS', i_opendns, success_opendns, count)
                    json.dump(label_dict_opendns, open("%s/filters/opendns.json" % (Constants.TARGET_DIR), "w"))
                label_dict_opendns[req['dst_url']] = []
                try:
                    parse_opendns(req, label_dict_opendns)
                    success_opendns += 1
                except Exception as e:
                    print('Open DNS failed,', req['dst_url'])#, e)
                #print(label_dict_opendns)
                time.sleep(0.5)

            if (req['dst_url'] not in label_dict_mcafee) or (req['dst_url'] not in security_dict_mcafee):
                i_mcafee += 1
                if i_mcafee % 100 == 0:
                    mcafee_headers, mcafee_token1, mcafee_token2 = mcafee.setup()
                if i_mcafee % 300 == 0:
                    print('MacFee', i_mcafee, success_mcafee, count)
                    json.dump(label_dict_mcafee, open("%s/filters/mcafee_category.json" % (Constants.TARGET_DIR), "w"))
                    json.dump(security_dict_mcafee, open("%s/filters/mcafee_security.json" % (Constants.TARGET_DIR), "w"))
                label_dict_mcafee[req['dst_url']] = []
                security_dict_mcafee[req['dst_url']] = 'Unverified'
                try:
                    s = parse_mcafee(req, label_dict_mcafee, security_dict_mcafee, mcafee_headers, mcafee_token1, mcafee_token2)
                    if s:
                        success_mcafee += 1
                    else:
                        print('McaFee failed 1,', req['dst_url'])
                except Exception as e:
                    print('McaFee failed 2,', req['dst_url'], e)
                    mcafee_headers, mcafee_token1, mcafee_token2 = mcafee.setup()
                    try:
                        s = parse_mcafee(req, label_dict_mcafee, security_dict_mcafee, mcafee_headers, mcafee_token1, mcafee_token2)
                        if s:
                            success_mcafee += 1
                        else:
                            print('McaFee failed 3,', req['dst_url'])
                    except Exception as e:
                        print('McaFee failed 4,', req['dst_url'], e)
                #print(label_dict_mcafee)
                time.sleep(0.5)
        
    json.dump(label_dict_opendns, open("%s/filters/opendns.json" % (Constants.TARGET_DIR), "w"))
    json.dump(label_dict_mcafee, open("%s/filters/mcafee_category.json" % (Constants.TARGET_DIR), "w"))
    json.dump(security_dict_mcafee, open("%s/filters/mcafee_security.json" % (Constants.TARGET_DIR), "w"))


if __name__ == "__main__":
    for vpn in Constants.DVPNs:
        print('get_labels', vpn)
        try:
            get_label('%s/jsons/requests_%s.json' % (Constants.TARGET_DIR, vpn))
        except Exception as e:
            print('failed!', e)

'''
if __name__ == "__main__":
    #for vpn in Constants.DVPNs:
    for vpn in ['tachyon']:
        #for node in Constants.NODES:
        for node in ['aws-us']:
            print('get_labels', vpn, node)
            try:
                get_label('%s/jsons/requests_%s_%s.json' % (Constants.TARGET_DIR, node, vpn))
            except Exception as e:
                print('failed!', e)
#'''