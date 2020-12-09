import cherrypy
import random
import json
from cherrypy.lib.static import serve_file
import logging

import os
current_dir = os.path.dirname(os.path.abspath(__file__))

import sys
sys.path.append(os.getcwd() + '/..')
#import nc_helper
import helpers

def read_json(req): 
	cl = req.headers['Content-Length']
	rawbody = req.body.read(int(cl))
	body = json.loads(rawbody)
	#print(body)
	return body 


@cherrypy.expose
class RingWebService(object):
    def __init__(self):
        self.dvpns = ['mysterium', 'sentinel', 'tachyon']

    #@cherrypy.tools.accept(media='text/plain')
    def GET(self, var=None, **params):
        cherrypy.log("GET!!!")
        cherrypy.log(var)
        cherrypy.log(str(params))
        url_splits = cherrypy.url().split('/')
        if 'action' in params:
            page = url_splits[-1]
            if params['action'] == 'status':
                # cherrypy.response.headers["Content-Type"] = "application/json"
                if page in self.dvpns:
                    cherrypy.log("test_dvpn")
                    return json.dumps({
                        "eth-address": "0x13kjhk", 
                        "data-plan": 123,
                        "used-data": 12412523100,
                        "bandwidth-limit": 200,
                        "auto-bandwidth": True,
                        "price-setting": 0.01,
                        "auto-price": False,
                    })
                elif page == 'index':
                    cherrypy.log("test_index")
                    return json.dumps({
                        "block-p2p": {
                            "block-p2p-edk": True, 
                            "block-p2p-dc": True, 
                            "block-p2p-kazaa": True, 
                            "block-p2p-gnu": True, 
                            "block-p2p-bit": True, 
                            "block-p2p-apple": True, 
                            "block-p2p-winmx": False, 
                            "block-p2p-soul": True, 
                            "block-p2p-ares": True, 
                        }, "block-risk": {
                            "block-risk-Medium": True, 
                            "block-risk-High": True, 
                            "block-risk-Unverified": True, 
                        }, "block-content": {
                            "block-content-Pornography": True, 
                            "block-content-Potential Criminal Activities": True, 
                            "block-content-Potential Illegal Software": True, 
                            "block-content-Illegal UK": True, 
                            "block-content-Malicious Downloads": True, 
                            "block-content-Malicious Sites": True, 
                            "block-content-Phishing": True, 
                            "block-content-PUPs": True, 
                            "block-content-Spam URLs": True, 
                            "block-content-Browser Exploits": True, 
                            "block-content-P2P/File Sharing": True, 
                            "block-content-Spyware/Adware/Keyloggers": True,
                        }
                    })
                elif page == 'password':
                    cherrypy.log("test_password")
                    pass
                else:
                    cherrypy.log("test_else")
                    pass # wrong page!
            elif params['action'] == 'netstat':
                cherrypy.log("test_netstat")
                return json.dumps({
                    "mysterium": [
                        { "time": 1451523456789, "bps": 71},
                        { "time": 1451523456799, "bps": 711},
                        { "time": 1451523456809, "bps": 70},
                        { "time": 1451523456819, "bps": 712},
                        { "time": 1451523456829, "bps": 75},
                        { "time": 1451523456839, "bps": 126},
                    ],
                    "sentinel": [
                        { "time": 1451523456789, "bps": 171},
                        { "time": 1451523456799, "bps": 511},
                        { "time": 1451523456809, "bps": 270},
                        { "time": 1451523456819, "bps": 412},
                        { "time": 1451523456829, "bps": 85},
                        { "time": 1451523456839, "bps": 136},
                    ],
                })
            elif params['action'] == 'running-status':
                return "Running"
            elif params['action'] == 'start':
                return "Running"
            elif params['action'] == 'restart':
                return "Restarting"
            elif params['action'] == 'terminate':
                return "Inactive"
        
        elif (url_splits[-1] == "index"):
            return serve_file(os.path.join(current_dir, "index.html"), content_type='text/html')

        elif (url_splits[-1] == "password"):
            return serve_file(os.path.join(current_dir, "password.html"), content_type='text/html')
            
        elif (url_splits[-1] in self.dvpns):
            return serve_file(os.path.join(current_dir, "dvpn.html"), content_type='text/html')
        
        else:
            cherrypy.response.status = 404
            return "ERROR"
            
    def POST(self, var=None, **params):
        ret_code = 200
        result = []
        ans = ''

        cherrypy.log("POST!!!")
        body = read_json(cherrypy.request)
        cherrypy.log(str(body))
        if len(body) > 0:
            ans = 'OK\n'
            cherrypy.response.status = ret_code
        return ans.encode('utf8')

    def PUT(self, another_string):
        return 'PUT'

    def DELETE(self):
        return 'DELETE'


CP_CONF = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            # 'tools.staticdir.on': True,
            # 'tools.staticdir.dir': os.path.abspath(os.getcwd())
        }
}

if __name__ == '__main__':
    cherrypy.config.update({'server.socket_port': 45679})
    cherrypy.quickstart(RingWebService(), '/', CP_CONF)