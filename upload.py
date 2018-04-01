import os
import hmac
import hashlib
import urllib
import paramiko

class Uploader():
	def __init__(self, log, dry_release):
		self.log = log

                self.ssh_key = paramiko.Ed25519Key.from_private_key_file('../keys/id_ed25519')
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
		elif arch.startswith('darwin-amd64-'):
			return 'darwin64-gcc'
		else:
			raise Exception('Unsupported architecture: %s' % arch)

	def nightly_file(self, build_type, filename, stream, uuid, hgid, arch):
		if self.dry_release:
			if stream is not None:
				target_path = '/home/ck/public_html/dry-release/%s' % os.path.basename(filename)
				self.log.write('Dry run: Copying to %s\n' % target_path)

				content = stream.read()
				open(target_path, 'w').write(content)
		else:
			if stream is not None:
				# If stream is nil the build failed
				self.log.write('Uploading nightly file %s...\n' % os.path.basename(filename))

				content = stream.read()
				filehash = hmac.new(self.nightly_key, content, hashlib.sha256).hexdigest()

				remote_dir = 'nightly/snapshots'
				remote_filename = '%s/%s' % (remote_dir, os.path.basename(filename))

                                # Upload the file
                                with self._connect_sftp() as sftp:
                                        try:
                                                sftp.mkdir(remote_dir)
                                        except IOError:
                                                # If the directory exists already IOError is raised
                                                pass
                                        with sftp.file(remote_filename, 'w') as f:
                                                f.write(content)
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

			response = urllib.urlopen('https://www.openclonk.org/nightly-builds/', urllib.urlencode(parameters))
			if response.getcode() != 200:
				raise Exception('Upload failed: %s' % response.read())

	def release_file(self, filename, (major, minor)):
		self.log.write('Uploading release file %s...\n' % os.path.basename(filename))

		if self.dry_release:
			target_path = '/home/ck/public_html/dry-release/%s' % os.path.basename(filename)
			self.log.write('Dry run: Copying to %s\n' % target_path)

			content = open(filename, 'r').read()
			open(target_path, 'w').write(content)

			return target_path, None
		else:
			filehash = hmac.new(self.release_key, open(filename, 'r').read(), hashlib.sha256).hexdigest() # TODO: strip?

			remote_dir = 'release/%d.%d' % (major, minor)
			remote_filename = '%s/%s' % (remote_dir, os.path.basename(filename))

			# Upload the file
                        with self._connect_sftp() as sftp:
                                try:
                                        sftp.mkdir(remote_dir)
                                except IOError:
                                        # If the directory exists already IOError is raised
                                        pass
                                sftp.put(filename, remote_filename)

			return remote_filename, filehash
			
	def release_binaries(self, filename, arch, (major, minor)):
		(remote_filename, filehash) = self.release_file(filename, (major, minor))
		if not self.dry_release:
		
			self.log.write('Registering update at openclonk.org %s...\n' % os.path.basename(filename))
			parameters = {
				'new_version': '%d.%d' % (major, minor),
				'file': remote_filename,
				'platform': self.get_masterserver_archname(arch),
				'hash': filehash
			}

			response = urllib.urlopen('https://www.openclonk.org/update/', urllib.urlencode(parameters))
#			response = urllib.urlopen('http://localhost:3526', urllib.urlencode(parameters))
			if response.getcode() != 200:
				raise Exception('Upload failed: %s' % response.read())

        def _connect_sftp(self):
                transport = paramiko.Transport(('openclonk.org', 22))
                # TODO: Host key verification?
                transport.connect(hostkey=None, username='builds', pkey=self.ssh_key)
                return paramiko.SFTPClient.from_transport(transport)
