#!/usr/bin/env python

import sys
from time import time
import shelve
from atlas import *

targeting_resolvers   = set()
scheduled_resolvers   = shelve.open('shelves/resolvers-scheduled.db')
dns_query_resolvers   = dns( '_5001._tcp.cheetara.huque.com'
                           , 'TLSA'
                           , description = 'Can query TLSA record'
                           , is_public = True
                           , do = True
			   , cd = True
                           , prepend_probe_id = False
                           , udp_payload_size = 4096
			   , retry = 3
                           )

targeting_8888   = set()
scheduled_8888   = shelve.open('shelves/8888-scheduled.db')
dns_query_8888   = dns( '_5001._tcp.cheetara.huque.com'
                           , 'TLSA'
                           , description = 'Can query TLSA record'
                           , is_public = True
			   , target = '8.8.8.8'
			   , recursion_desired = True
                           , do = True
			   , cd = True
                           , prepend_probe_id = False
                           , udp_payload_size = 4096
			   , retry = 3
                           )


def schedule(experiment, dns_query, scheduled, targeting):
	print( 'targeting %d probes for experiment %s'
	     % (len(targeting), experiment))
	try:
		r = atlas.create( dns_query
				, map(int, targeting)
				)
	except Exception, e:
		print(repr(e))
		print(e.read())
		raise e

	print( 'measurement for submitted: %s' % repr(r))
	msm_id = r['measurements'][0]
	for prb_id in targeting:
		scheduled[prb_id] = msm_id
	scheduled.sync()

for p in atlas.probe(status=1, limit=100):
	prb_id = str(p['id'])

	if prb_id not in scheduled_resolvers:
		targeting_resolvers.add(prb_id)
	if len(targeting_resolvers) == 1000:
		schedule(          'resolvers', dns_query_resolvers
		        , scheduled_resolvers , targeting_resolvers )
		targeting_resolvers = set()

	if prb_id not in scheduled_8888:
		targeting_8888.add(prb_id)
	if len(targeting_8888) == 1000:
		schedule(          '8888', dns_query_8888
		        , scheduled_8888 , targeting_8888 )
		targeting_8888 = set()


if len(targeting_resolvers) > 50:
	schedule(          'resolvers', dns_query_resolvers
	        , scheduled_resolvers , targeting_resolvers )
else:
	print('not scheduling resolvers, targeted # probes too small: %d\n'
	     % len(targeting_resolvers))

if len(targeting_8888) > 50:
	schedule(          '8888', dns_query_8888
	        , scheduled_8888 , targeting_8888 )
else:
	print('not scheduling 8888, targeted # probes too small: %d\n'
	     % len(targeting_8888))


scheduled_resolvers.close()
scheduled_8888.close()

