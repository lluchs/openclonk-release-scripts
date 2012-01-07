import os
import time
import zipfile

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

			zip_filename = os.path.join(directory, filename + '.zip')
			z = zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED)

			for filename, stream in contentiter.ContentIter():
				z.writestr(filename, stream.read())

			arch_iter = architer.ArchIter(arch)
			for filename, stream in arch_iter:
				z.writestr(filename, stream.read())
			uuid = arch_iter.uuid

			z.close()

			try:
				uploader = upload.Uploader(self.log)
				uploader.nightly_file(zip_filename, uuid, rev, arch)
				os.unlink(zip_filename)
			except autobuild.AutobuildException as ex:
				upload.nightly_upload(None, ex.uuid) # make an entry for "failed build"

		os.rmdir(directory)
