import paramiko

class SSHHandler:

	def __init__(self, ip, user, password):
		self.ssh = paramiko.SSHClient()
		self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		self.ip = ip
		self.user = user
		self.password = password

	def connect(self):
		self.ssh.connect(self.ip, username=self.user, password=self.password, timeout=10)
		
	def execute(self, cmd):		
		stdin, stdout, stderr = self.ssh.exec_command(cmd)
		stdin.close()
		data = stdout.read()
		return data

	def disconnect(self):
		self.ssh.close()

	# can be used to get config files from SM.
	def sftp(self, localpath, remotepath):
		self.sftp = self.ssh.open_sftp()
		self.sftp.get(remotepath, localpath)
		self.sftp.close()
		# read up: http://docs.paramiko.org/en/2.0/api/sftp.html#paramiko.sftp_client.SFTPClient

