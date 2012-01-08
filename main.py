import os
import sys

import hg
#import release
import notifyqueue
import pushtrigger
#import snapshotbuilder

class BuildServer():
	def __init__(self):
		self.log = sys.stderr #open('oc-release.log', 'w')

		if not os.path.exists('openclonk'):
			self.log.write('Openclonk Repository does not exist. Cloning...\n')
			hg.clone('http://hg.openclonk.org/openclonk')
			self.log.write('Repository created\n')

		os.chdir('openclonk')

		# Register triggers
		self.queue = notifyqueue.NotifyQueue()
		self.pushtrigger = pushtrigger.PushTrigger(self.queue, self.log)

	def run(self):
		# Run main event loop
		while True:
			job = self.queue.get()

			# TODO: Descriptive job name, so we can log here what we are gonna do

			try:
				if not job():
					self.log.write('Job requests exiting. Exiting.\n')
					return
			except Exception as ex:
				self.log.write('Job failed to finish: %s\n' % ex)

#	def make_release(self, revision):
#		try:
#			builder = release.ReleaseBuilder(self.log)
#			builder.run(revision)
#		except Exception as ex:
#			self.log.write('Failed to release revision %s: %s\n' % (revision, ex))
#			raise

try:
	server = BuildServer()
	server.run()

#	queue = notifyqueue.NotifyQueue()
#	nightly_engine = nightlyenginebuilder.NightlyEngineBuilder(queue, server.log)
#	nightly_engine.run_periodic()

#	snapshot = snapshotbuilder.SnapshotBuilder('82f4d93ae0c7', server.log)
#	snapshot()

#	server.make_release('f6f897a10645')

except Exception as ex:
	print 'A fatal error occured:'
	print '  ' + str(ex)

	raise
