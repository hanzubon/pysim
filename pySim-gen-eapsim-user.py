#!/usr/bin/env python

#
# Utility to run the GSM algorithm on the SIM card
# for EAP-SIM RADIUS authenticated user file
#
# Copyright (C) 2009  Sylvain Munaut <tnt@246tNt.com>
# Copyright (C) 2010  Harald Welte <laforge@gnumonks.org>
# Copyright (C) 2013  Alexander Chemeris <alexander.chemeris@gmail.com>
# Copyright (C) 2016  Yuki MIZUNO <mizuyuu0904@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import hashlib
from optparse import OptionParser
import os
import random
import re
import sys
import csv

try:
	import json
except ImportError:
	# Python < 2.5
	import simplejson as json

from pySim.commands import SimCardCommands
from pySim.utils import h2b, swap_nibbles, rpad, dec_imsi, dec_iccid


def parse_options():

	parser = OptionParser(usage="usage: %prog [options]")

	parser.add_option("-d", "--device", dest="device", metavar="DEV",
			help="Serial Device for SIM access [default: %default]",
			default="/dev/ttyUSB0",
		)
	parser.add_option("-b", "--baud", dest="baudrate", type="int", metavar="BAUD",
			help="Baudrate used for SIM access [default: %default]",
			default=9600,
		)
	parser.add_option("-p", "--pcsc-device", dest="pcsc_dev", type='int', metavar="PCSC",
			help="Which PC/SC reader number for SIM access",
			default=None,
		)

	(options, args) = parser.parse_args()

	if args:
		parser.error("Extraneous arguments")

	return options


if __name__ == '__main__':

	# Parse options
	opts = parse_options()

	# Connect to the card
	if opts.pcsc_dev is None:
		from pySim.transport.serial import SerialSimLink
		sl = SerialSimLink(device=opts.device, baudrate=opts.baudrate)
	else:
		from pySim.transport.pcsc import PcscSimLink
		sl = PcscSimLink(opts.pcsc_dev)

	# Create command layer
	scc = SimCardCommands(transport=sl)

	# Wait for SIM card
	sl.wait_for_card()

	# Program the card
	#print("Reading ...")

	# EF.IMSI
	(res, sw) = scc.read_binary(['3f00', '7f20', '6f07'])
	if sw == '9000':
		print("# IMSI: %s" % (dec_imsi(res),))
	else:
		sys.stderr.write("IMSI: Can't read, response code = %s" % (sw,))

	imsi = dec_imsi(res)

	with open('hnilist.csv', 'r') as f:
		reader = csv.reader(f)
		for row in reader:
			if row[0] == imsi[:6] or row[0] == imsi[:5]:
				print '# ' + row[2]
				mcc = row[3]
				mnc = row[4]
				if len(mnc) == 2:
					mnc = '0' + mnc
				break
		

	# RUN GSM ALGORITHM
	print('1%s@wlan.mnc%s.mcc%s.3gppnetwork.org  Auth-Type := EAP, EAP-Type := SIM' % (imsi, mnc, mcc))
	for i in range(3):
		rand = os.urandom(16).encode('hex')
		(res, sw) = scc.run_gsm(rand)
		if sw == '9000':
			SRES, Kc = res[:8], res[8:]
			print('%8s%s%d = 0x%s,' % ('', 'EAP-Sim-Rand', i+1, rand))
			print('%8s%s%d = 0x%s,' % ('', 'EAP-Sim-SRES', i+1, SRES))
			print('%8s%s%d = 0x%s,' % ('', 'EAP-Sim-KC', i+1, Kc))
		else:
			sys.stderr.write("GSM: Can't run, response code = %s" % (sw,))
			break

