import os
import time
import zipfile

import hg
import arches
import upload
import autobuild
import periodicbuilder

class NightlyEngineBuilder(periodicbuilder.PeriodicBuilder):
	def __init__(self, queue, log):
		# Build once every night at 3am
		fix = time.mktime((2000, 1, 1, 3, 0, 0, 0, 0, -1))
		interval = 3600 * 24

		periodicbuilder.PeriodicBuilder.__init__(self, queue, fix, interval)

		self.log = log

	def run_periodic(self):
		# TODO: Exception safety

		hg.pull()
		hg.update('default')

		rev = hg.id()

		# TODO: Use StringIO to write zipfile to memory
		directory = 'nightly-engine'

		try:
			os.mkdir(directory)
		except Exception as ex:
			# TODO: Only pass if directory exists already
			pass

		for arch in arches.arches:
			try:
				# obtain an engine build
				engineX, uuid = autobuild.obtain(rev, arch, ['clonk'])

				filename, stream = engineX[0]
				base, ext = os.path.splitext(filename)

				date = time.strftime('%Y%m%d')
				new_filename = 'openclonk-engine-%s-%s-%s' % (date, rev, arch)
#				engine_path = os.path.join(directory, new_filename + ext)
#				os.rename(os.path.join(directory, engineX[0]), engine_path)

				zip_filename = os.path.join(directory, new_filename + '.zip')
				z = zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED)
				z.writestr(new_filename + ext, stream.read())
				z.close()
				#os.unlink(engine_path)

				uploader = upload.Uploader(self.log)
				uploader.nightly_file(zip_filename, uuid, rev, arch)
				os.unlink(zip_filename)
			except autobuild.AutobuildException as ex:
				uploader = upload.Uploader(self.log)
				uploader.nightly_file(None, ex.uuid, rev, arch) # make an entry for "failed build"

		os.rmdir(directory)
