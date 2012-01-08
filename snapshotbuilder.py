import os
import time
import zipfile
import tarfile
import StringIO

import periodicbuilder
import hg
import arches
import autobuild
import upload
import contentiter
import architer

class SnapshotBuilder(periodicbuilder.PeriodicBuilder):
	def __init__(self, queue, log):
		# Build once every night at 3am
		fix = time.mktime((2000, 1, 1, 3, 0, 0, 0, 0, -1))
		interval = 3600 * 24

		periodicbuilder.PeriodicBuilder.__init__(self, queue, fix, interval)

		self.log = log

	def run_periodic(self):
		# TODO: Exception safety

		# TODO: Run on specified revision ID
		hg.pull()
		hg.update('default')
		rev = hg.id()

		# TODO: Use StringIO to write zipfile to memory
		directory = 'nightly-snapshot'

		try:
			os.mkdir(directory)
		except Exception as ex:
			# TODO: Only pass if directory exists already
			pass

		# TODO: Use a tarball on Linux, and make sure access rights for
		# executables are properly set.
		for arch in arches.arches:
			date = time.strftime('%Y%m%d')
			filename = 'openclonk-snapshot-%s-%s-%s' % (date, rev, arch)

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
				uploader.nightly_file(archive_name(filename), uuid, rev, arch)
				os.unlink(archive_name(filename))
			except autobuild.AutobuildException as ex:
				uploader = upload.Uploader(self.log)
				uploader.nightly_file(None, ex.uuid, rev, arch) # make an entry for "failed build"

		os.rmdir(directory)
