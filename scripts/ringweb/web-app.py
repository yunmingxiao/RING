import cherrypy
import random
import json
from cherrypy.lib.static import serve_file
import logging

import os
current_dir = os.path.dirname(os.path.abspath(__file__))

import sys
sys.path.append(os.getcwd() + '/..')
import nc_helper
from helpers import web2controller

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
        self.controller = nc_helper.Controller(os.getcwd() + '/..')

    #@cherrypy.tools.accept(media='text/plain')
    def GET(self, var=None, **params):
        cherrypy.log("GET!!!")
        cherrypy.log(str(var), str(params))
        url_splits = cherrypy.url().split('/')
        page = url_splits[-1]
        if 'action' in params:
            if params['action'] == 'status':
                # cherrypy.response.headers["Content-Type"] = "application/json"
                if page in self.dvpns:
                    cherrypy.log("test_vpn" + str(self.controller.get_config(page)))
                    return json.dumps(self.controller.get_config(page))
                elif page == 'index':
                    cherrypy.log("test_index" + str(self.controller.get_access()))
                    return json.dumps(self.controller.get_access())
                elif page == 'password':
                    pass
                else:
                    cherrypy.response.status = 404
                    return "ERROR"
            elif params['action'] == 'netstat':
                h = json.dumps(self.controller.get_history())
                cherrypy.log("test_netstat" + str(h))
                return h
            elif params['action'] == 'running-status':
                pass
                # return self.controller.get_status(page)
            elif params['action'] == 'start':
                self.controller.start(page)
                # return "Starting..."
            elif params['action'] == 'restart':
                self.controller.reboot(page)
                # return "Restarting..."
            elif params['action'] == 'terminate':
                self.controller.terminate(page)
                # return "Terminating..."
            return self.controller.get_status(page)
        
        elif (page == "index"):
            return serve_file(os.path.join(current_dir, "index.html"), content_type='text/html')

        elif (page == "password"):
            return serve_file(os.path.join(current_dir, "password.html"), content_type='text/html')
            
        elif (page in self.dvpns):
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

        url_splits = cherrypy.url().split('/')
        if (url_splits[-1] == "index"):
            self.controller.update_access(web2controller(body))

        elif (url_splits[-1] == "password"):
            pass # TODO
            
        elif (url_splits[-1] in self.dvpns):
            self.controller.update_vpn(url_splits[-1], body)
        
        else:
            cherrypy.response.status = 404
            return "ERROR"

        return ans.encode('utf8')

    def PUT(self, another_string):
        return 'PUT'

    def DELETE(self):
        return 'DELETE'


if __name__ == '__main__':
    CP_CONF = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True,
            'tools.response_headers.on': True,
            # 'tools.staticdir.on': True,
            # 'tools.staticdir.dir': os.path.abspath(os.getcwd())
        }
    }

    server_config={
        'server.socket_host': '0.0.0.0',
        'server.socket_port': 45679,
        # 'server.ssl_module':'builtin',
        # 'server.ssl_certificate':'certificate.pem',
    }

    cherrypy.config.update(server_config)
    cherrypy.quickstart(RingWebService(), '/', CP_CONF)