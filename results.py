#!/usr/bin/env python

import sys
from time import time
import shelve
from atlas import *
import dpkt
import base64

def good_result(res):
	has_tlsa = False
	has_sig = False
	try:
		d = dpkt.dns.DNS(base64.b64decode(res['abuf']))
	except dpkt.dpkt.UnpackError:
		return 0
	except IndexError:
		return 0
	if [rr for rr in d.an if rr.type == 52 and rr.name.lower() ==
	                            '_5001._tcp.cheetara.huque.com']:
		has_tlsa = True

	if [rr for rr in d.an if rr.type == 46 and rr.name.lower() ==
	                            '_5001._tcp.cheetara.huque.com']:
		has_sig = True

	return 1 if has_sig and has_tlsa else 0


for experiment in ('resolvers', '8888'):
	scheduled = shelve.open('shelves/%s-scheduled.db' % experiment)
	completed = shelve.open('shelves/%s-completed.db' % experiment)
	noresults = shelve.open('shelves/%s-noresults.db' % experiment)
	succeeded = shelve.open('shelves/%s-succeeded.db' % experiment)

	msm_status = dict()
	msm_result = dict()
	successes = fails = 0

	for (prb_id, msm_id) in scheduled.iteritems():
		if prb_id in completed or prb_id in noresults:
			continue

		if msm_id not in msm_status:
			msm_status[msm_id] = atlas.msm(msm_id).next()['status']['id']
			if msm_status[msm_id] > 3:
				msm_results = dict()
				for r in  atlas.result(msm_id).next():
					msm_prb_id = str(r['prb_id'])
					if msm_prb_id not in msm_results:
						msm_results[msm_prb_id] = list()
					msm_results[msm_prb_id].append(r)
				msm_result[msm_id] = msm_results
		if msm_status[msm_id] <= 3:
			continue

		results = msm_result[msm_id].get(prb_id, [])
		if len(results) == 0:
			noresults[prb_id] = True
			continue
		completed[prb_id] = results

		success = list()
		for result in results:
			if 'resultset' in result:
				successes = 0
				for r in result['resultset']:
					if 'result' in r:
						successes += good_result(r['result'])
			elif 'result' in result:
				successes = good_result(result['result'])
			else:
				successes = 0
			success.append(1 if successes else 0)

		if float(sum(success)) / float(len(success)) >= 0.75:
			succeeded[prb_id] = results
		elif prb_id in succeeded:
			del succeeded[prb_id]

	print( ( 'experiment: %10s, scheduled %4d, '
	       + 'participated: %4d (%5.2f%%), succeeded: %4d (%5.2f%%)' )
	     % ( experiment
	       , len(scheduled)
	       , len(completed), 100.0 * len(completed) / len(scheduled)
	       , len(succeeded), 100.0 * len(succeeded) / max(1
                                                             , len(completed))
	       ))

	succeeded.close()
	noresults.close()
	completed.close()
	scheduled.close()
