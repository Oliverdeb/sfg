import json

class FileHandler:

	def __init__(self, file_name, path):
		found = True
		try:
			self.file = open('uploads/'+file_name, 'r')
			self.data = json.load(self.file)
			self.file.close()
		except (IOError):
			print "File not found!"
			found = False

		# second method using the path / might work on windows and not linux?
		# need to test
		if found: return
		print "didnt find first way trying second"
		try:
			self.file = open(path, 'r')
			self.data = json.loads(self.file.read())
			self.file.close()
		except ( IOError):
			print "File not found!"



	def get_salt_master_ips(self):
		return self.data["saltmasters"]

	def get_user_name(self):
		return self.data["username"]

	def get_password(self):
		return self.data["password"]

	def get_cmc_ips(self):
		return self.data["cmc_ips"]


