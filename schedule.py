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

for p in atlas.probe(status=1):
	prb_id = str(p['id'])

	if prb_id not in scheduled_resolver:
		targeting_resolver.add(prb_id)
	if len(targeting_resolver) == 1000:
		schedule(          'resolver', dns_query_resolver
		        , scheduled_resolver , targeting_resolver )
		targeting_resolver = set()


if len(targeting_baseline) > 50:
	schedule(          'baseline', dns_query_baseline
	        , scheduled_baseline , targeting_baseline )
else:
	print('not scheduling baseline, targeted # probes too small: %d\n'
	     % len(targeting_baseline))

scheduled_baseline.close()

