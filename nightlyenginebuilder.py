import os
import time
import zipfile

import hg
import arches
import upload
import autobuild

class NightlyEngineBuilder():
	def __init__(self, revision, log):
		self.revision = revision
		self.log = log

	def __call__(self):
		# TODO: Exception safety
		hg.update(self.revision)

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
				engineX, uuid = autobuild.obtain(self.revision, arch, ['clonk'])

				filename, stream = engineX[0]
				base, ext = os.path.splitext(filename)

				date = time.strftime('%Y%m%d')
				new_filename = 'openclonk-engine-%s-%s-%s' % (date, self.revision, arch)

				zip_filename = os.path.join(directory, new_filename + '.zip')
				z = zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED)
				z.writestr(new_filename + ext, stream.read())
				z.close()

				uploader = upload.Uploader(self.log)
				uploader.nightly_file(zip_filename, uuid, self.revision, arch)
				os.unlink(zip_filename)
			except autobuild.AutobuildException as ex:
				uploader = upload.Uploader(self.log)
				uploader.nightly_file(None, ex.uuid, self.revision, arch) # make an entry for "failed build"

		os.rmdir(directory)
		return True
