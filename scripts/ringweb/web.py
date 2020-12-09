#!/usr/bin/python
import random
import string
import json
import cherrypy
import os
from threading import Thread
import threading
import signal
import sys
import time 
import simplejson
#import argparse
#import xmlrpclib
#from geoip import geolite2
import subprocess
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
import socket
import requests 
sys.path.insert(0, '~/dvpn/scripts/ringweb')
#import db_manager
#from db_manager import insert_addon_list, clean_uid, get_info, get_infos, insert_crawled_addon, crawl_addon_list

try:
    from geoip import geoiplite2 as geolite2
except:
    from geoip import geolite2

# simple function to read json from a POST message 
def read_json(req): 
	cl = req.headers['Content-Length']
	rawbody = req.body.read(int(cl))
	body = simplejson.loads(rawbody)
	#print(body)
	return body 


# global parameters
port = 5555                               # default listening port 
THREADS = []                              # list of threads 

# function to run a bash command
def run_bash(bashCommand, verbose = True):
	process = subprocess.Popen(bashCommand.split(), stdout = subprocess.PIPE, stdin =subprocess.PIPE, shell = False)
	output, error = process.communicate()
	if verbose:
		print(output)
		print(error)

def CORS():
	cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"

def cors():
  # logging 
  print("inside cors()")
  if cherrypy.request.method == 'OPTIONS':
    # logging 
    print("received a pre-flight request")
    # preflign request 
    # see http://www.w3.org/TR/cors/#cross-origin-request-with-preflight-0
    cherrypy.response.headers['Access-Control-Allow-Methods'] = 'POST'
    cherrypy.response.headers['Access-Control-Allow-Headers'] = 'content-type'
    cherrypy.response.headers['Access-Control-Allow-Origin']  = '*'
    # tell CherryPy no avoid normal handler
    return True
  else:
    cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'


# thread to control client-server communication
def web_app():
    # configuration 
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True,
            'tools.response_headers.on': True,
        }
    }

    cherrypy.tools.cors = cherrypy._cptools.HandlerTool(cors)
    server_config={
        'server.socket_host': '0.0.0.0',
        'server.socket_port': port,
        #'server.ssl_module':'builtin',
        #'server.ssl_certificate':'certificate.pem',
    }
    cherrypy.config.update(server_config)

    # restful APIs
    cherrypy.tree.mount(StringGeneratorWebService(), '/updateWalletAddress', conf)
    cherrypy.tree.mount(StringGeneratorWebService(), '/UpdateDVPN', conf)
    cherrypy.tree.mount(StringGeneratorWebService(), '/dVPNStatus', conf)
    
    # start cherrypy engine 
    cherrypy.engine.start()
    cherrypy.engine.block()


# catch ctrl-c
def signal_handler(signal, frame):

	# logging 
	print('You pressed Ctrl+C!')

	# kill throughput thread 
	print("stopping throughput thread")
	THREADS[0].do_run = False
	THREADS[0].join()
	
	# kill cherrypy
	print("stopping cherrypy webapp")
	cherrypy.engine.exit()

	# exiting from main process
	sys.exit(0)


@cherrypy.expose
class StringGeneratorWebService(object):

	@cherrypy.tools.accept(media='text/plain')
	def GET(self, var=None, **params):
		
		# log last IP that contacted the server
		src_ip = cherrypy.request.headers['Remote-Addr']
		
		# check status of an addon  
		if 'checkAddon' in cherrypy.url() and 'addon' in cherrypy.request.params: 
			addon = cherrypy.request.params['addon']
			#print("Checking info for addon  %s" %(addon))
			info, msg = get_info(addon)
			if info is not None:
				# respond with addon info 
				cherrypy.response.status = 200
				msg += "\nStatus for addon " + addon + ":" + info[0][0]
			else:
				# respond with error which occurred 
				print("Addon %s not found" %(addon))
				cherrypy.response.status = 202
				msg += "\nAddon not found"
		else:
				cherrypy.response.status = 404
				msg = "ERROR: missing addon key parameter in GET request"
		
		# all good 
		msg += "\n"
		return msg.encode('utf8')


	# handle POST requests 
	def POST(self, name="test"):

		# parameters 
		ret_code = 202	   # default return code 
		result = []        # result to be returned when needed 
		ans = ''           # placeholder for response 
		ret_list = {}	   # return addon info list

		# extract incoming IP address 
		src_ip = cherrypy.request.headers['Remote-Addr']

		# update on an addon (from crawler) 
		if 'addonStatus' in cherrypy.url():
			# read JSON data posted 
			body = read_json(cherrypy.request)
			info = ''
			timestamp = None 
			container_name = 'default'
			machine = 'localhost'
			if 'info' not in body and 'name' not in body['info']:
				msg = 'addon name or its info are missing'
			else: 
				addon_id = body['info']['name']
				if 'timestamp' in body: 
					timestamp = body['timestamp']
				if 'container_name' in body: 
					container_name = body['container_name']
				if 'machine' in body: 
					machine = body['machine']
				msg = insert_crawled_addon(addon_id, body['info'], timestamp, container_name, machine)
			return  msg + "\n"
	
		# list of installed addons was received 
		elif 'addonList' in cherrypy.url():
			# read JSON data posted 
			try:
				body = read_json(cherrypy.request)
			except:
				body = {}
			uid = None 
			addon_list, user_setting = [], []
			if 'uid' in body: 
				uid = body['uid']
			if 'addon_list' in body: 
				addon_list = body['addon_list']
			if 'user_setting' in body: 
				user_setting = body['user_setting']
			#print(uid, addon_list, user_setting)
			if uid is not None and len(addon_list) > 0: 
				#print("inserting in db")
				insert_addon_list(uid, addon_list, user_setting, ip = src_ip)
				crawl_addon_list(g_control_server=CONTROLER_ADDR, uid=uid, addon_list=addon_list)
			else: 
				print("error, no db insertion --  either uid is missing or empty addon list")
			
			try:
				info, msg = get_infos(addon_list)
				ret_list = json.dumps(info)
				if msg:
					print(msg)
			except Exception as e:
				print("Return addon status list error. ", e)
	
		
		# respond all good 
		#cherrypy.response.headers['Content-Type'] = 'application/json'
		cherrypy.response.headers['Content-Type'] = 'string'
		cherrypy.response.headers['Access-Control-Allow-Origin']  = '*'
		cherrypy.response.status = ret_code
		ans = 'OK\n'
		if len(ret_list) > 3:
			ans = str(ret_list)
		print(ans)

		# all good, send response back 
		return ans.encode('utf8')

	def OPTIONS(self, name="test"): 
		# preflign request 
		# see http://www.w3.org/TR/cors/#cross-origin-request-with-preflight-0
		cherrypy.response.headers['Access-Control-Allow-Methods'] = 'POST'
		cherrypy.response.headers['Access-Control-Allow-Headers'] = 'content-type'
		cherrypy.response.headers['Access-Control-Allow-Origin']  = '*'

	def PUT(self, another_string):
		cherrypy.session['mystring'] = another_string

	def DELETE(self):
		cherrypy.session.pop('mystring', None)

# main goes here 
if __name__ == '__main__':

	# start a thread which handle client-server communication 
	THREADS.append(Thread(target = web_app()))
	THREADS[-1].start()
	
	# listen to Ctrl+C
	signal.signal(signal.SIGINT, signal_handler)
	signal.pause()
