#!/usr/bin/env python

import urllib2, urllib, json, os, sys
from pprint import pprint
from datetime import datetime, timedelta
from time import time

API_URL = 'https://atlas.ripe.net'

def api_path(*path, **args):
	return '/api/v1/%s?%s' % ( '/'.join(map(str, path))
	                         , urllib.urlencode(args))

def update_defaults(d, **defaults):
	d.update((k, v) for k, v in defaults.items() if k not in d)

class Atlas:
	def __init__(self, create_key = None, result_key = None):
		if not create_key:
			with file('%s/.atlas/auth' % os.path.expanduser('~')) \
			as f:
				keys_l = f.read().strip().split()
				create_key = keys_l[0]
				if not result_key and len(keys_l) > 1:
					result_key = keys_l[1]
		self.create_key  = create_key

		if not result_key:
			result_key = create_key
		self.result_key  = result_key

		redirect_handler = urllib2.HTTPRedirectHandler()
		cookie_handler   = urllib2.HTTPCookieProcessor()
		self.opener      = urllib2.build_opener( redirect_handler
		                                       , cookie_handler )

	def __getattr__(self, name):
		def get(*path, **args):
			update_defaults(args, key = self.result_key, limit = 0)
			url = api_path(name, *path, **args)
			while url:
				try:
					r = self.opener.open(API_URL + url)
				except urllib2.HTTPError, e:
					print 'get "' + API_URL + url + '"'
					print e
					print e.read()
					r = self.opener.open(API_URL + url)

				assert r.getcode() / 100 == 2
				s = r.read()
				try:
					j = json.loads(s)
				except ValueError:
					j = eval(s)
				if 'objects' not in j or 'meta'    not in j:
					yield j
					return
				for obj in j['objects']:
					yield obj
				url = j['meta'].get('next', None)
		return get

	def msm(self, *path, **args):
		return self.measurement(*path, **args)

	def result(self, msm_id):
		return self.measurement(msm_id, 'result')

	def create(self, definitions, *probes):

		probes = list(probes)
		req = { 'definitions': definitions if type(definitions) is list
		                                   else [definitions]
		      , 'probes'     : list()
		      }

		for key in ('stop_time', 'start_time'):
			if not probes: break
			if   type(probes[-1]) in (int, float):
				req[key] = int(probes[-1])
			elif type(probes[-1]) is datetime:
				req[key] = int(probes[-1].strftime("%s"))
			else:
				break
			probes.pop()

		for probe in probes:
			if type(probe) is list:
				req['probes'].append(
					{ 'requested': len(probe)
					, 'type'    : 'probes'
					, 'value'   : ','.join(map(str, probe))
					})
			elif type(probe) is dict:
				req['probes'].append(probe)
			else:
				raise Exception( "Unknown probe type: %s" 
				               % repr(probe))

		url = API_URL + api_path('measurement/', key = self.create_key)
		try:
			r = self.opener.open( urllib2.Request( url, json.dumps(req)
					    , {'Content-Type': 'application/json'}))
		except urllib2.HTTPError, e:
			print 'post "' + url + '"'
			print e
			print e.read()
			r = self.opener.open( urllib2.Request( url, json.dumps(req)
					    , {'Content-Type': 'application/json'}))

		assert r.getcode() / 100 == 2
		return json.loads(r.read())

def msm_defaults(kwargs, **defaults):
	update_defaults(defaults, description = kwargs.get('description', '')
	                        , is_oneoff = 'interval' not in kwargs
			        , af = 4)
	update_defaults(kwargs  , **defaults)
	return dict([(k, v) for k, v in kwargs.items() if v is not None])

def dns(query_argument, query_type = 'A', target = None, **kwargs):
	return msm_defaults( kwargs, type = 'dns', query_class = 'IN'
	                   , query_argument = query_argument
	                   , query_type = query_type, target = target
			   , use_probe_resolver = target is None
			   , recursion_desired  = target is None
			   )

def dns6(query_argument, qtype = 'TXT', target = None, **kwargs):
	return dns(query_argument, qtype, target, af = 6, **kwargs)

def msm_constructor(msm_type, **params):
	def constructor(target, **kwargs):
		return msm_defaults( kwargs, type = msm_type
		                   , target = target, **params)
	return constructor

ping        = msm_constructor('ping')
ping6       = msm_constructor('ping', af = 6)
traceroute  = msm_constructor('traceroute', protocol = 'ICMP')
traceroute6 = msm_constructor('traceroute', protocol = 'ICMP', af = 6)
sslcert     = msm_constructor('sslcert')
sslcert6    = msm_constructor('sslcert', af = 6)

def probes(amount, p_type, value):
	return { 'requested': amount, 'type': p_type, 'value': value }

def probes_WW(amount):
	return probes(amount, 'area', 'WW')

try:
	atlas = Atlas()
except:
	atlas = None

### Examples
#
### Import atlas
#
# from atlas import *
#
#
### Get a list of all probes
# 
# probes = atlas.probe(prefix_v6 = '::/0', limit = 0)
# 
#
### Filter probes that are up
#
# probes = filter(lamba p: p['status'] == 1, probes)
#
#
### Create a one off dns6 measurement
#
# definition = dns6('ripe67.nlnetlabs.nl', 'AAAA', '2001:7b8:40:1:d0e1::1')
# r = atlas.create(definition, probes_ww(500))
#
#
### Create periodic dns6 measurement (each 20 minutes, ends after 100 minutes)
#
# definition = dns6('ripe67.nlnetlabs.nl', 'AAAA', '2001:7b8:40:1:d0e1::1'
#                  , interval = 20 * 60)
# r = atlas.create(definition, probes_ww(500), time() + 20 * 60 * 5.5)
#
#
### Check on status of measurement
#
# atlas.measurement(r['measurements'][0])
#
#
### Check result of measurement
#
# atlas.result(r['measurements'][0])
#
#
