import os
import hmac
import hashlib
import urllib
import ftplib

class Uploader():
	def __init__(self, log):
		self.log = log

		self.release_key = open('../keys/key-boom.txt').read().strip()
		self.nightly_key = open('../keys/key-ck.txt').read().strip()

	def get_masterserver_archname(self, arch):
		if arch.startswith('win32-x86-'):
			platform = 'win-x86'
		elif arch.startswith('win32-x64-'):
			platform = 'win-x86_64'
		elif arch.startswith('linux-x86-'):
			platform = 'linux-x86'
		elif arch.startswith('linux-x64-'):
			platform = 'linux-x86_64'
		else:
			raise Exception('Unsupported architecture: %s' % arch)

	def nightly_file(self, filename, uuid, hgid, arch):
		if filename is not None:
			# If filename is nil the build failed
			self.log.write('Uploading nightly file %s...\n' % os.path.basename(filename))

			filehash = hmac.new(self.nightly_key, open(filename, 'r').read(), hashlib.sha256).hexdigest()

			remote_dir = 'nightly/engines'
			remote_filename = '%s/%s' % (remote_dir, os.path.basename(filename))

			# Upload the file
			ftp = ftplib.FTP('ftp.openclonk.org', 'ftp1144497-nightly', open('../passwd/nightly.txt', 'r').read().strip())
			try:
				ftp.mkd(remote_dir)
			except ftplib.error_perm:
				# If the directory exists already errorperm is raised
				pass
			ftp.storbinary('STOR %s' % remote_filename, open(filename, 'r'))
		else:
			# In case of a build failure, make a message hash of the UUID
			remote_filename = None
			filehash = hmac.new(self.nightly_key, uuid, hashlib.sha256).hexdigest()

		# Now call the nightly page
		parameters = {
			'hgid': hgid,
			'type': 'engine',
			'uuid': uuid,
			'digest': filehash,
			'platform': arch,
			'user': 'ck'
		}

		if remote_filename is not None:
			parameters.update({'file': remote_filename})

		# TODO: Evaluate server response

		response = urllib.urlopen('http://openclonk.org/nightly-builds/index.php', urllib.urlencode(parameters))
		if response.getcode() != 200:
			raise Exception('Upload failed: %s' % response.read())

	def release_file(self, filename, arch, (major, minor, micro), oldversions):
		self.log.write('Uploading release file %s...\n' % os.path.basename(filename))

		filehash = hmac.new(self.release_key, open(filename, 'r').read(), hashlib.sha256).hexdigest() # TODO: strip?

		remote_dir = 'release/%d.%d.%d' % (major, minor, micro)
		remote_filename = '%s/%s' % (remote_dir, os.path.basename(filename))

		# Upload the file
		ftp = ftplib.FTP('ftp.openclonk.org', 'ftp1144497-nightly', open('../passwd/nightly.txt', 'r').read().strip())

		try:
			ftp.mkd(remote_dir)
		except ftplib.error_perm:
			# If the directory exists already errorperm is raised
			pass

		ftp.storbinary('STOR %s' % remote_filename, open(filename, 'r'))

		# Register the uploaded file with the masterserver
		parameters = {
			'action': 'release-file',
			'old_version': ','.join(map(lambda (x,y,z): '%d.%d.%d' % (x,y,z), oldversions)),
			'new_version': '%d.%d.%d' % (major, minor, micro),
			'file': remote_filename,
			'platform': self.get_masterserver_archname(arch),
			'hash': filehash
		}

		urllib.urlopen('http://boom.openclonk.org/server/index.php', urllib.urlencode(parameters))
#		urllib.urlopen('http://localhost:3526', urllib.urlencode(parameters))
