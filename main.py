#!/usr/bin/env python

from flask import Flask, render_template, request, redirect
import os
import sys
import json

sys.path.append(sys.path[0]+ "/src/")

import SSHutil
import fileutil
import threading
import paramiko
import pdfkit
import subprocess
import excelgenerator
import SNMPhandler
import easysnmp
from collections import OrderedDict

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = 'uploads'

salt_master_ssh_connections = {}
salt_masters = {}
node_idrac_ips = {}
headings = []
dontdisplay=[ 'kernelrelease', 'os', 'osrelease', 'sm',
			'hwaddr_interfaces', 'saltversion','osfull',
			'num_cpus', 'biosversion', 'SSDs']

@app.route("/")
def main():
	return render_template('index.html')


def condense_fields(salt_masters):
	""" iterates through all the nodes and creates a combined IP field """
	global headings
	for ip, nodes in salt_masters.iteritems():

		if nodes == "Could not connect to server":
			continue
		for node in nodes:
			if node == "sm":
				continue

			salt_masters[ip][node].update(\
				{'osfull': \
					salt_masters[ip][node]['os'] + " " + salt_masters[ip][node]['osrelease'],\
				}\
			)
			mb = int(salt_masters[ip][node]['mem_total'])
			salt_masters[ip][node]['mem_total'] = str(round(mb/1000.0, 2))+"GB"


			if headings == []:
				headings = salt_masters[ip][node].keys()
			for k in salt_masters[ip][node].keys():
				if k not in headings:
					headings += [k]

def worker(conn):
	global salt_masters
	try:
		conn.connect()
		conn.execute("salt \"*\" saltutil.refresh_modules")
		result = conn.execute("salt \"*\" grains.items --out=json --static")		
		conn.disconnect()
	except(paramiko.ssh_exception.NoValidConnectionsError):
		result = None
		webconf = None
	salt_masters[conn.ip] = json.loads(result) if result is not None else "Could not connect to server"
	if webconf is None:
		return
	
	webconf = json.loads(webconf)
	sm = webconf["Common"]["SaltMasterHostname"]
	salt_masters[conn.ip]['sm'] = sm
	for server in webconf["Server"]:

		node = server['Hostname']

		if not node in salt_masters[conn.ip]:
			continue

		salt_masters[conn.ip][node]['web_conf_ip'] = {}
		salt_masters[conn.ip][node]['services'] = []

		for interface in server['Interface']:
			if salt_masters[conn.ip][node]['ip4_interfaces'][interface['Name']] != interface["IP"]:
				salt_masters[conn.ip][node]['web_conf_ip'][interface['Name']] = interface["IP"]

		salt_masters[conn.ip][node]['sm'] = True if node == sm else False

	for mclass in webconf['MachineClass']:
		for node in mclass['Host']:
			if not node in salt_masters[conn.ip]:
				continue
			salt_masters[conn.ip][node]['services'].append(mclass['Name'])

	return

def parse_ip4(output):
	output = output.split("\n")
	for line in output:
		if not "IP Address" in line:
			continue
		line = line.split("= ")
		return line[1]
	return ""

def get_cmc_info(conn):
	global node_idrac_ips
	conn.connect()
	output = conn.execute("getsvctag")
	results = output.split("\n")
	print "\nSSHing into CMC:"
	print conn.ip
	for result in results:
		temp = result
		if "Server" not in temp:
			continue
		temp = temp.split(" ", 1)
		test = temp[1].split("\t", 1)
		stripped = temp
		if len(test) > 1:
			stripped = [temp[0]]+  [test[0].strip(' \t')]

		service_tag = stripped[1].strip(' \t')
		if service_tag == '' or 'N/A' in service_tag or "Extension" in service_tag:
			continue

		server_number = stripped[0]
		ip4 = parse_ip4(conn.execute("getniccfg -m " + server_number))

		node_idrac_ips[service_tag] = ip4

	conn.disconnect()

def get_info_snmp(conn, key, k):
	print "running SNMP to iDRAC " + conn.ip
	global salt_masters	
	dimm_info = conn.memory()
	num_cpus = conn.cpu()
	drive_info = conn.drives()
	raid_cards = conn.raid_cards()
	idrac_ver = conn.idrac_version()

	if num_cpus != "None":
		if num_cpus == 0: num_cpus += 1
		existing = salt_masters[key][k]['cpu_model'] 
		salt_masters[key][k]['cpu_model'] = str(num_cpus) +"x " + existing.replace("(R)","")

	salt_masters[key][k]['dimms'] = dimm_info
	salt_masters[key][k]['drives'] = drive_info
	salt_masters[key][k]['raid_cards'] = raid_cards
	salt_masters[key][k]['idrac_ver'] = idrac_ver

	
def get_grains(file):
	""" get grains.items from all specified salt masters
		SSH into CMCs and get IPs of iDRACs for servers
		send snmp requests to iDRACs and update information """

	salt_ips = file.get_salt_master_ips()
	cmc_ips = file.get_cmc_ips()

	global salt_master_ssh_connections

	# initialise SSH handling objects to interface with SSHing to salt masters
	salt_master_ssh_connections = map(lambda ip: \
		SSHutil.SSHHandler(ip, file.get_user_name(), file.get_password()),\
		salt_ips)

	cmc_ssh_conns = map(lambda (ip, user_and_pass): \
		SSHutil.SSHHandler(ip, user_and_pass['username'], user_and_pass['password']),\
		cmc_ips.iteritems())

	global salt_masters
	global headings
	import timeit
	start_time = timeit.default_timer()	

	threads = map(lambda c: threading.Thread(target=worker, args=(c,)), salt_master_ssh_connections )
	extra_threads = map(lambda c: threading.Thread(target=get_cmc_info, args=(c,)), cmc_ssh_conns)
	threads = threads + extra_threads		

	for t in threads:
		t.start()
	for t in threads:
		t.join()

		# start SSH session and execute command, parse result as json and store in a dictionary
	global node_idrac_ips


	idrac_threads = []
	idrac_snmp_conns = []
	for key,value in salt_masters.iteritems():
		if value == "Could not connect to server":
			continue
		for k, v in value.iteritems():
			if k == 'sm':
				continue
			svc_tag = salt_masters[key][k]['serialnumber']

			product = salt_masters[key][k]['productname']
			salt_masters[key][k]['productname'] = product.replace("PowerEdge ", "")
			if svc_tag in node_idrac_ips:
				ip = node_idrac_ips[svc_tag]
				salt_masters[key][k]['iDRAC_ip'] = ip

				print "found a tag  " + svc_tag +" and ip is " +ip
				conn = SNMPhandler.snmp_wrapper(ip, svc_tag)
				idrac_snmp_conns.append(conn)
				idrac_threads.append(threading.Thread(target=get_info_snmp, args=(conn,key,k)))
			else:
				salt_masters[key][k]['iDRAC_ip'] = "None"
				salt_masters[key][k]['dimms'] = "None"
				salt_masters[key][k]['drives'] = "None"
				salt_masters[key][k]['raid_cards'] = "None"
				salt_masters[key][k]['idrac_ver'] = "None"
				# salt_masters[key][k]['raid_versions'] = "None"

	for t in idrac_threads:
		t.start()
	for t in idrac_threads:
		t.join()
	condense_fields(salt_masters)

	print timeit.default_timer() - start_time

	return salt_masters

@app.route('/upload', methods=['POST'])
def upload():
	global headings
	global dontdisplay
	file = request.files['file']
	if file.filename ==  "": # check for accepted file exensions - json /txt /cfg only 
		return redirect("/", code=302)
	directory_path = os.path.dirname(os.path.abspath(__file__))
	folder = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
	path = directory_path + '/' +   folder	

	# save file
	file.save(folder)
	input_file = fileutil.FileHandler(file.filename, path)
	return render_template("output.html", grains=get_grains(input_file), headings=headings, dontdisplay=dontdisplay)

@app.route('/testing')
def test():
	return "Success"

@app.route('/render_table')
def render_table():
	global dontdisplay
	global salt_masters
	global headings
	key = request.args.get('key')

	return render_template("rendertable.html", grains=salt_masters, headings=headings, dontdisplay=dontdisplay, todisplay=key)

@app.route('/generate_pdf')
def generate_pdf():
	global headings
	global salt_masters
	global dontdisplay
	sel = request.args.get('selected')
	key = request.args.get('key')
	sel = sel.replace("[", "")
	sel = sel.replace("]", "")
	sel = sel.replace("\"", "")
	sels = sel.split(",")
	htmlpdf = render_template('tabletopdf.html', grains=salt_masters, headings=sels, todisplay=key )
	css=[sys.path[0]+'/static/css/bootstrap.min.css']
	key = "all" if key == "*" else key
	
	path = 'out/'+ key + '.pdf'

	pdfkit.from_string(htmlpdf, 'out/'+ key + '.pdf', css=css)

	filexplorer = "explorer /select," if "Win" in sys.platform else "xdg-open"

	subprocess.Popen([filexplorer, sys.path[0] + "/" + path])
	return sys.path[0] +"/" + path

@app.route('/generate_excel')
def generate_excel():
	global salt_masters
	global headings
	excel = excelgenerator.workbook_generator()
	path = excel.toexcel(salt_masters, headings, ['sm', 'volumes', 'osrelease'])
	print path
	filexplorer = "explorer /select," if "Win" in sys.platform else "xdg-open"

	subprocess.Popen([filexplorer, sys.path[0] + "/" + path])
	return sys.path[0] + "/" + path

if __name__ == "__main__":
	subprocess.Popen(['google-chrome', 'http://127.0.0.1:5000'])
	app.run()

