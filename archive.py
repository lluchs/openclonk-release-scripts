import time
import zipfile
import tarfile
import StringIO

import architer

class Archive():
	def __init__(self, arch, fileobj):
		self.arch = arch
		self.init_time = time.time()

		if 'win32' in self.arch:
			self.archive = zipfile.ZipFile(fileobj, 'w', zipfile.ZIP_DEFLATED)
		elif 'darwin' in self.arch:
			self.archive = fileobj # it is already a zip file
		else:
			self.archive = tarfile.open(fileobj = fileobj, mode = 'w:bz2')

	def get_filename(self, basename):
		if 'win32' in self.arch:
			return basename + '.zip'
		elif 'darwin' in self.arch:
			return basename + '.zip'
		else:
			return basename + '.tar.bz2'

	def add(self, filename, content):
		if 'win32' in self.arch:
			self.archive.writestr(filename, content)
		elif 'darwin' in self.arch:
			if not hasattr(self, 'archive_written'):
				self.archive.write(content)
				self.archive_written = True
			else:
				raise Exception('Only one file allowed for Darwin')
		else:
			info = tarfile.TarInfo(filename)
			if architer.ArchIter.is_executable(filename):
				info.mode = 0755
			else:
				info.mode = 0644
			info.mtime = self.init_time
			info.size = len(content) # TODO: Would be cool if this could be dedcude automatically when reading the fileobj in addfile...
			self.archive.addfile(info, StringIO.StringIO(content))

	def close(self):
		if 'darwin' not in self.arch :
			self.archive.close()
