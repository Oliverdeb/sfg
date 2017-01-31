from easysnmp import Session, EasySNMPTimeoutError

""" This class serves as the easysnmp wrapper"""
class  snmp_wrapper:

	# pass in iDRAC ip and service tag of machine
	def __init__(self, ip, svc_tag):
		self.ip = ip
		self.svc_tag = svc_tag
		self.session = Session(hostname=ip, community="public", version=2)
		self.oids = {
			"memory_speed":"iso.3.6.1.4.1.674.10892.5.4.1100.50.1.15",\
			"memory_size":"iso.3.6.1.4.1.674.10892.5.4.1100.50.1.14",\
			"cpu":"iso.3.6.1.4.1.674.10892.5.4.1100.30.1.2",\
			"drive_names": "iso.3.6.1.4.1.674.10892.5.5.1.20.130.4.1.6",\
			"drive_capacities" :"iso.3.6.1.4.1.674.10892.5.5.1.20.130.4.1.11",\
			"raid_cards":"iso.3.6.1.4.1.674.10892.5.5.1.20.130.1.1.2",\
			"raid_card_versions":"iso.3.6.1.4.1.674.10892.5.5.1.20.130.1.1.8",\
			"idrac_version":"iso.3.6.1.4.1.674.10892.5.4.300.60.1.11" 
		}
		
		
	def __walk(self, oid):
		return self.session.walk(oid)

	def __get(self, oid):
		return self.session.get(oid)

	def memory(self):

		""" returns the number of modules and individual dimm information """

		try:
			speed = self.__walk(self.oids['memory_speed'])
			capacity = self.__walk(self.oids['memory_size'])
		except EasySNMPTimeoutError:
			return "None"

		if speed == [] or capacity == []:
			return "None"

		number_of_dims= len(capacity)
		output_string = ""
		dimms = {}
		
		for cap, spd in zip(capacity, speed):
			dimms[str(int(cap.value)/1048576) + " " + str(spd.value)] =0

		for cap, spd in zip(capacity, speed):
			dimms[str(int(cap.value)/1048576) + " " + str(spd.value)] += 1
		
		for i,(k,v) in enumerate(dimms.iteritems()):
			if i != 0:
				output_string += ", "
			data = k.split(" ")
			output_string += str(v) +"x" + data[0]+"GB" + " @ " + data[1] + "MHz"

		return output_string

	def cpu(self):

		""" returns the number of cpus (salt provides the cpu info, just not how many) """

		try:
			number_of_cpus = self.__walk(self.oids['cpu'])
		except EasySNMPTimeoutError:
			return "None"

		return len(number_of_cpus)



	def drives(self):

		""" returns the drives and their capacities """

		try:
			drive_names = self.__walk(self.oids['drive_names'])
			drive_caps = self.__walk(self.oids['drive_capacities'])
		except:
			return 'None'

		if drive_names == [] or drive_caps == []:
			return 'None'

		drives = {}
		for name, cap in zip(drive_names, drive_caps):
			drives[name.value+ "`" + str((int(cap.value)/1024))+"GB"] = 0

		for name, cap in zip(drive_names, drive_caps):
			drives[name.value+ "`" + str((int(cap.value)/1024))+"GB"] += 1

		output_string = ""
		for i,(k,v) in enumerate(drives.iteritems()):
			if i != 0:
				output_string += ", "
			# print k
			data = k.split("`")
			output_string += str(v) + "x " + data[0] + " " + data[1]
		return output_string

	def raid_cards(self):

		""" returns the raid controllers and their firmware versions """

		try:
			raid_cards = self.__walk(self.oids['raid_cards'])
			versions = self.__walk(self.oids['raid_card_versions'])
		except:
			return "None"

		if raid_cards == [] or versions == []:
			return "None"
		raid_controllers = {}

		for name, version in zip(raid_cards, versions):
			raid_controllers[name.value + "`" + version.value] = 0

		for name, version in zip(raid_cards, versions):
			raid_controllers[name.value + "`" + version.value] += 1

		output_string = ""
		for i,(k,v) in enumerate(raid_controllers.iteritems()):
			if i != 0:
				output_string += ", "
			data = k.split("`")
			data[0] = data[0].replace("Embedded", "")
			data[0] = data[0].replace("()", "")
			data[0] = data[0].replace("Mini", "")
			output_string += str(v) + "x " + data[0] + "firmware ver: " + data[1]
		return output_string

	def idrac_version(self):

		""" returns the idrac version """

		try:
			ver = self.__walk(self.oids['idrac_version'])
		except:
			return "None"

		if ver == []:
			return "None"
		return ver[0].value