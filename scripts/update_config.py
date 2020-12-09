import json
import sys

def update_eth(eth_addr):
    config = json.load(open('../resources/sentinel/config.data', 'r'))
    config['account_addr'] = eth_addr
    json.dump(config, open('../resources/sentinel/config.data', 'w'))

def update_price(price_per_gb):
    config = json.load(open('../resources/sentinel/config.data', 'r'))
    config['price_per_gb'] = float(price_per_gb)
    json.dump(config, open('../resources/sentinel/config.data', 'w'))

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print('usage: python3 update_config.py eth/price eth_addr/price')
        exit()
    if sys.argv[1] == 'eth':
        update_eth(sys.argv[2])
    elif sys.argv[1] == 'price':
        update_price(sys.argv[2])
    else:
        print('usage: python3 update_config.py eth/price eth_addr/price')