import os
import sys
import pika

import git
import log
import releasebuilder
import snapshotbuilder
import docbuilder
import notifyqueue
import pushtrigger
import xmltrigger

class BuildServer():
	def __init__(self):
		self.log = log.Log('logs/oc-release.log')

		# Setup AMQP connection
		sslkey = os.path.normpath(os.path.join(os.getcwd(), 'keys/ockey.pem'))
		sslcert = os.path.normpath(os.path.join(os.getcwd(), 'keys/CIA-londeroth.org.pem'))

		amqp_params = pika.ConnectionParameters(
                        host='amqp.nosebud.de',
                        port=5671,
                        virtual_host='openclonk',
                        ssl=True,
                        ssl_options={'keyfile': sslkey, 'certfile': sslcert},
                        credentials=pika.credentials.ExternalCredentials(),
                        )
		self.amqp_connection = pika.BlockingConnection(amqp_params)

		if not os.path.exists('openclonk'):
			self.log.write('Openclonk Repository does not exist. Cloning...\n')
			git.clone('git://git.openclonk.org/openclonk')
			self.log.write('Repository created\n')

		os.chdir('openclonk')

		# Register triggers
		self.queue = notifyqueue.NotifyQueue()
		self.pushtrigger = pushtrigger.PushTrigger(self.amqp_connection, self.queue, self.log)
		self.xmltrigger = xmltrigger.XMLTrigger(self.amqp_connection, self.queue, self.log)

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
			builder = releasebuilder.ReleaseBuilder(self.amqp_connection, revision, self.log)
			builder()
		except Exception as ex:
			self.log.write('Failed to release revision %s: %s\n' % (revision, ex))
			raise

	def make_snapshot(self, revision, dry_release):
		try:
			builder = snapshotbuilder.SnapshotBuilder(self.amqp_connection, revision, self.log, 'openclonk', dry_release)
			#builder = snapshotbuilder.SnapshotBuilder(revision, self.log, 'mape', dry_release)
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
#	server.make_snapshot('origin/master', True)
#	server.make_docs('master')
	server.run()

except Exception as ex:
	print 'A fatal error occured:'
	print '  ' + str(ex)

	raise
