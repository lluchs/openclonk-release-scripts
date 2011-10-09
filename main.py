import os
import sys

import hg
import release

class BuildServer():
	def __init__(self):
		self.log = sys.stderr #open('oc-release.log', 'w')

		if not os.path.exists('openclonk'):
			self.log.write('Openclonk Repository does not exist. Cloning...\n')
			hg.clone('http://hg.openclonk.org/openclonk')
			self.log.write('Repository created\n')

		os.chdir('openclonk')

	def make_release(self, revision):
		try:
			builder = release.ReleaseBuilder(self.log)
			builder.run(revision)
		except Exception as ex:
			self.log.write('Failed to release revision %s: %s\n' % (revision, ex))
			raise

try:
	server = BuildServer()
#	server.make_release('99bd2ab9f906')
	server.make_release('f6f897a10645')
except Exception as ex:
	print 'A fatal error occured:'
	print '  ' + str(ex)

	raise
