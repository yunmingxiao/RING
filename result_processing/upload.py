# send the information to controller

import requests
import Constants

CONTROLLER = 'http://165.124.180.66:45678/'

def upload_file(path, filename):
    print('uploading', path, filename)
    try:
        with open(path+filename, 'r') as fp:
            requests.post(CONTROLLER+filename, files={'data': fp})
    except Exception as e:
        print('Upload failed!', filename, e)

upload_file('../scripts/config/', 'netstat.log')
upload_file('../scripts/config/', 'operation.log')
upload_file('../scripts/config/', 'default_result.json')
        
upload_file('%s/filters/' % (Constants.TARGET_DIR), 'mcafee_category.json')
upload_file('%s/filters/' % (Constants.TARGET_DIR), 'mcafee_security.json')

for vpn in Constants.DVPNs:
    upload_file('%s/jsons/' % (Constants.TARGET_DIR), 'requests_%s.json' % (vpn))
    upload_file('%s/jsons/' % (Constants.TARGET_DIR), 'vpn_conns_%s.json' % (vpn))