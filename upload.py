import os
import hmac
import hashlib
import urllib
import ftplib
import StringIO

class Uploader():
	def __init__(self, log, dry_release):
		self.log = log

		self.release_key = open('../keys/key-boom.txt').read().strip()
		self.nightly_key = open('../keys/key-ck.txt').read().strip()

		self.dry_release = dry_release

	def get_masterserver_archname(self, arch):
		if arch.startswith('win32-i386-'):
			return 'win-x86'
		elif arch.startswith('win32-amd64-'):
			return 'win-x86_64'
		elif arch.startswith('linux-i386-'):
			return 'linux-x86'
		elif arch.startswith('linux-amd64-'):
			return 'linux-x86_64'
		else:
			raise Exception('Unsupported architecture: %s' % arch)

	def nightly_file(self, build_type, filename, stream, uuid, hgid, arch):
		if stream is not None:
			# If stream is nil the build failed
			self.log.write('Uploading nightly file %s...\n' % os.path.basename(filename))

			content = stream.read()
			filehash = hmac.new(self.nightly_key, content, hashlib.sha256).hexdigest()

			remote_dir = 'nightly/snapshots'
			remote_filename = '%s/%s' % (remote_dir, os.path.basename(filename))

			# Upload the file
			ftp = ftplib.FTP('ftp.openclonk.org', 'ftp1144497-nightly', open('../passwd/nightly.txt', 'r').read().strip())
			try:
				ftp.mkd(remote_dir)
			except ftplib.error_perm:
				# If the directory exists already errorperm is raised
				pass
			ftp.storbinary('STOR %s' % remote_filename, StringIO.StringIO(content))
		else:
			# In case of a build failure, make a message hash of the UUID
			remote_filename = None
			filehash = hmac.new(self.nightly_key, uuid, hashlib.sha256).hexdigest()

		# Now call the nightly page
		parameters = {
			'type': build_type,
			'hgid': hgid,
			'uuid': uuid,
			'digest': filehash,
			'platform': arch,
			'user': 'ck'
		}

		if remote_filename is not None:
			parameters.update({'file': remote_filename})

		response = urllib.urlopen('http://openclonk.org/nightly-builds/index.php', urllib.urlencode(parameters))
		if response.getcode() != 200:
			raise Exception('Upload failed: %s' % response.read())

	def release_file(self, filename, (major, minor, micro)):
		self.log.write('Uploading release file %s...\n' % os.path.basename(filename))

		if self.dry_release:
			target_path = '/home/ck/public_html/dry-release/%s' % os.path.basename(filename)
			self.log.write('Dry run: Copying to %s\n' % target_path)

			content = open(filename, 'r').read()
			open(target_path, 'w').write(content)
		else:
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

			return remote_filename, filehash
			
	def release_binaries(self, filename, arch, (major, minor, micro), oldversions):
		(remote_filename, filehash) = self.release_file(filename, (major, minor, micro))
		if !self.dry_release:
		
			self.log.write('Registering with masterserver %s...\n' % os.path.basename(filename))
			# Register the uploaded file with the masterserver
			parameters = {
				'action': 'release-file',
				'old_version': ','.join(map(lambda (x,y,z): '%d.%d.%d' % (x,y,z), oldversions)),
				'new_version': '%d.%d.%d' % (major, minor, micro),
				'file': remote_filename,
				'platform': self.get_masterserver_archname(arch),
				'hash': filehash
			}

			response = urllib.urlopen('http://boom.openclonk.org/server/index.php', urllib.urlencode(parameters))
#			response = urllib.urlopen('http://localhost:3526', urllib.urlencode(parameters))
			if response.getcode() != 200:
				raise Exception('Upload failed: %s' % response.read())
