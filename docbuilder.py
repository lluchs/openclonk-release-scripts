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

class DocBuilder():
	def __init__(self, revision, log):
		self.revision = revision
		self.log = log
		self.name = 'Documentation update for revision %s' % revision

	def __call__(self):
		# TODO: Exception safety
		hg.update(self.revision)

		# Build the documentation
		make.make('docs')

		# TODO: We should try to deduce the available languages
		# automatically.
		langs = ['de', 'en']

		ftp = ftplib.FTP('ftp.openclonk.org')
		ftp.login(username = 'ftp1144497-docs', 'PASSWORD GOES HERE')


		#date = time.strftime('%Y%m%d')

		make.run('docs')

		files = filter(lambda x,y,z: z.endswith('.php'), os.walkpath('docs/online'))

		for lang in langs:
			ftp.mkdir('%s-new' % lang)

			for filename in files:
				# TODO: Upload it!
				pass

		return True
