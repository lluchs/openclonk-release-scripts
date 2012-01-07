import os
import sys

import hg
import release
import notifyqueue
import nightlyenginebuilder
import snapshotbuilder

class BuildServer():
	def __init__(self):
		self.log = sys.stderr #open('oc-release.log', 'w')

		if not os.path.exists('openclonk'):
			self.log.write('Openclonk Repository does not exist. Cloning...\n')
			hg.clone('http://hg.openclonk.org/openclonk')
			self.log.write('Repository created\n')

		os.chdir('openclonk')

		# Register builders
#		self.queue = NotifyQueue()
#		self.nightly_engine = NightlyEngineBuilder(queue)

	def run(self):
		# Run main event loop
		while True:
			job = queue.get()
			if not job():
				return

	def make_release(self, revision):
		try:
			builder = release.ReleaseBuilder(self.log)
			builder.run(revision)
		except Exception as ex:
			self.log.write('Failed to release revision %s: %s\n' % (revision, ex))
			raise

try:
	server = BuildServer()

	queue = notifyqueue.NotifyQueue()
#	nightly_engine = nightlyenginebuilder.NightlyEngineBuilder(queue, server.log)
#	nightly_engine.run_periodic()

	snapshot = snapshotbuilder.SnapshotBuilder(queue, server.log)
	snapshot.run_periodic()

#	server.make_release('f6f897a10645')

except Exception as ex:
	print 'A fatal error occured:'
	print '  ' + str(ex)

	raise
