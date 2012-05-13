import os
import sys

import hg
import releasebuilder
import snapshotbuilder
import docbuilder
import notifyqueue
import pushtrigger

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
			self.log.write('Running job "%s".\n' % job.name)

			try:
				if not job():
					self.log.write('Job "%s" requests exiting. Exiting.\n' % job.name)
					return
				self.log.write('Job "%s" finished successfully.\n' % job.name)
			except Exception as ex:
				self.log.write('Job "%s" failed to finish: %s\n' % (job.name, ex))

	def make_release(self, revision):
		try:
			builder = releasebuilder.ReleaseBuilder(revision, self.log)
			builder()
		except Exception as ex:
			self.log.write('Failed to release revision %s: %s\n' % (revision, ex))
			raise

	def make_snapshot(self, revision):
		try:
			builder = snapshotbuilder.SnapshotBuilder(revision, self.log)
			builder()
		except Exception as ex:
			self.log.write('Failed to create snapshot for revision %s: %s\n' % (revision, ex))
			raise

	def make_docs(self, revision):
		try:
			builder = docbuilder.DocBuilder(revision, self.log)
			builder()
		except Exception as ex:
			self.log.write('Failed to update documentation for revision %s: %s\n' % (revision, ex))
			raise

try:
	server = BuildServer()

#	server.make_release('14ab9fe1345a') # 5.2.2
#	server.make_release('4c71d5edfb06') # 5.2.0
#	server.make_snapshot(hg.id())
#	server.make_docs(hg.id())
	server.run()

except Exception as ex:
	print 'A fatal error occured:'
	print '  ' + str(ex)

	raise
