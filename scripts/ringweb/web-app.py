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
        self.agree = self.get_agreement()

    def get_agreement(self):
        agreement = 'False'
        try:
            with open('user-agreement.txt', 'r') as fp:
                agreement = fp.read()
        except Exception as e:
            print('RingWebService.get_agreement', e)

        if agreement == 'True':
            return True
        else:
            return False

    def exec_agree(self, content):
        if content == 'True':
            self.agree = True
        else:
            self.agree = False
        with open('user-agreement.txt', 'w+') as fp:
            fp.write(content)

    #@cherrypy.tools.accept(media='text/plain')
    def GET(self, var=None, **params):
        cherrypy.log("GET!!!")
        cherrypy.log(str(var), str(params))
        url_splits = cherrypy.url().split('/')
        page = url_splits[-1]
        
        if (page == 'agreement'):
            return serve_file(os.path.join(current_dir, "agreement.html"), content_type='text/html')
        if (not self.agree):
            raise cherrypy.HTTPRedirect("/agreement")

        if 'action' in params:
            if params['action'] == 'status':
                # cherrypy.response.headers["Content-Type"] = "application/json"
                if page in self.dvpns:
                    cherrypy.log("test_vpn " + str(self.controller.get_config(page)))
                    return json.dumps(self.controller.get_config(page))
                elif page == 'index':
                    cherrypy.log("test_index " + str(self.controller.get_access()))
                    return json.dumps(self.controller.get_access())
                elif page == 'password':
                    pass
                else:
                    cherrypy.response.status = 404
                    return "ERROR"
            elif params['action'] == 'netstat':
                h = json.dumps(self.controller.get_history())
                # cherrypy.log("test_netstat" + str(h))
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
            elif params['action'] == 'errors':
                return self.controller.get_policy_errors()
            elif params['action'] == 'code':
                return self.controller.get_policy()
            elif params['action'] == 'schedule':
                return self.controller.get_schedule()
            elif params['action'] == 'restore_default':
                return self.controller.restore_default_policy()
            elif params['action'] == 'initiate':
                self.controller.update_vpn(page, {'initiated': True})
                cherrypy.log("test_init " + str(self.controller.get_config(page)))

            return self.controller.get_status(page)

        elif (var is None):
            raise cherrypy.HTTPRedirect("/index")

        elif (page == "index"):
            return serve_file(os.path.join(current_dir, "index.html"), content_type='text/html')

        elif (page == "password"):
            return serve_file(os.path.join(current_dir, "password.html"), content_type='text/html')
            
        elif (page in self.dvpns):
            return serve_file(os.path.join(current_dir, "dvpn.html"), content_type='text/html')
        
        elif (page == "tachyon_key.txt"):
            return serve_file(os.path.join(current_dir, "tachyon_key.txt"), content_type='text/html')

        else:
            cherrypy.response.status = 404
            return "ERROR"
            
    def POST(self, var=None, **params):
        ret_code = 200
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

        elif ('-custom-code' in url_splits[-1]):
            self.controller.update_policy(body['code'])
        elif ('-custom-schedule' in url_splits[-1]):
            cherrypy.log(url_splits[-2]))
            cherrypy.log(body)
            self.controller.update_vpn(url_splits[-2], body)
            cherrpy.log("custom_schedule update endpoint hit")
        
        else:
            cherrypy.log(url_splits)
            cherrypy.response.status = 404
            return "ERROR"

        return ans.encode('utf8')

    def PUT(self, var=None, **params):
        cherrypy.log("PUT!!!")
        cherrypy.log(str(var), str(params))

        if (var == 'agreement' and params['action'] == 'agree'):
            self.exec_agree('True')
            # raise cherrypy.HTTPRedirect("/index")
            return json.dumps({'redirect': cherrypy.url().replace('agreement', 'index')})
        elif (var == 'agreement' and params['action'] == 'disagree'):
            self.exec_agree('False')
            # raise cherrypy.HTTPRedirect("/index")
            return "SUCCESS"
        else:
            cherrypy.response.status = 404
            return "ERROR"

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