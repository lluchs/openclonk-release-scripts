import os
import time
import zipfile
import tarfile
import StringIO

import hg
import arches
import autobuild
import upload
import contentiter
import architer

class SnapshotBuilder():
	def __init__(self, revision, log):
		self.revision = revision
		self.log = log

	def __call__(self):
		# TODO: Exception safety
		hg.update(self.revision)

		# TODO: Use StringIO to write zipfile to memory
		directory = 'nightly-snapshot'

		try:
			os.mkdir(directory)
		except Exception as ex:
			# TODO: Only pass if directory exists already
			pass

		# TODO: Use same content streams for all architectures
		for arch in arches.arches:
			date = time.strftime('%Y%m%d')
			filename = 'openclonk-snapshot-%s-%s-%s' % (date, self.revision, arch)

			# TODO: Add an archive class...
			def archive_name(basename):
				if 'win32' in arch:
					return os.path.join(directory, basename + '.zip')
				else:
					return os.path.join(directory, basename + '.tar.bz2')

			def open_archive(basename):
				if 'win32' in arch:
					return zipfile.ZipFile(archive_name(basename), 'w', zipfile.ZIP_DEFLATED)
				else:
					return tarfile.open(archive_name(basename), 'w:bz2')

			def add_to_archive(archive, filename, content):
				if 'win32' in arch:
					archive.writestr(filename, content)
				else:
					info = tarfile.TarInfo(filename)
					if filename == 'clonk' or filename == 'c4group':
						info.mode = 0755
					else:
						info.mode = 0644
					info.mtime = time.time() # TODO: Should be the same for all files -- set once at the beginning
					info.size = len(content) # TODO: Would be cool if this could be dedcude automatically when reading the fileobj in addfile...
					archive.addfile(info, StringIO.StringIO(content))

			try:
				archive = open_archive(filename)
				for name, stream in contentiter.ContentIter():
					add_to_archive(archive, name, stream.read())

				arch_iter = architer.ArchIter(arch)
				for name, stream in arch_iter:
					add_to_archive(archive, name, stream.read())
				uuid = arch_iter.uuid
				archive.close()

				uploader = upload.Uploader(self.log)
				uploader.nightly_file(archive_name(filename), uuid, self.revision, arch)
				os.unlink(archive_name(filename))
			except autobuild.AutobuildException as ex:
				uploader = upload.Uploader(self.log)
				uploader.nightly_file(None, ex.uuid, self.revision, arch) # make an entry for "failed build"

		os.rmdir(directory)
		return True
