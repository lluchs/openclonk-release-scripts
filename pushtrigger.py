import pika
import json
import os

import trigger
import git
import snapshotbuilder
import releasebuilder
import docbuilder

class RevisionPushed():
	def __init__(self, amqp_connection, queue, log, revision):
		self.amqp_connection = amqp_connection
		self.queue = queue
		self.log = log
		self.revision = revision
		self.name = 'Analyze new commits after being notified about commit %s' % revision

	def __call__(self):
		self.log.write('New changesets have been pushed.\n')

		# See if the push changed something in the master branch
		git.reset('origin/master')
		current_id = git.id()
		git.fetch()
		git.reset(self.revision)

		if current_id != self.revision:
			self.log.write('The master branch has new commits.\n')

			# Make a new development snapshot
			builder = snapshotbuilder.SnapshotBuilder(self.amqp_connection, self.revision, self.log, 'openclonk', False)
			# TODO: Remove all other snapshot builders from the queue
			self.queue.put(50, builder)

			# Also make a new mape build. In principle we could do this only if something in the
			# mape directory or any of the other files used by mape change, but let's keep it simple here.
			builder = snapshotbuilder.SnapshotBuilder(self.amqp_connection, self.revision, self.log, 'mape', False)
			# TODO: Remove all other snapshot builders from the queue
			self.queue.put(70, builder)

			# See if something in the docs directory has changed
			log = git.log('docs', current_id, self.revision, 'oneline')
			if len(log) > 1 or (len(log) == 1 and log[0] != current_id):
				# TODO: Remove all other doc builders from the queue
				builder = docbuilder.DocBuilder(self.revision, self.log)
				self.queue.put(80, builder)

		else:
			self.log.write('The master branch has no new commits.\n')

		# TODO: Make a release if the version changed

		return True

class PushTrigger(trigger.Trigger):
	def __init__(self, amqp_connection, queue, log):
		self.amqp_connection = amqp_connection
		self.amqp_channel = amqp_connection.channel()
		trigger.Trigger.__init__(self, queue, log)

	def oc_release_build(self, channel, method, properties, payload):
		try:
			ref_update = json.loads(payload)
			# The routing key should already have ensured we're only getting
			# updates about the master branch
			assert ref_update['ref'] == 'refs/heads/master'

			# High priority to handle this revision push, it
			# will then queue the actual builders after
			# examining the nature of the new commits.
			self.queue.put(0, RevisionPushed(self.amqp_connection, self.queue, self.log, ref_update['commit']))
			channel.basic_ack(method.delivery_tag)
			return True
		except Exception, ex:
			channel.basic_reject(method.delivery_tag, requeue=False)
			return False, str(ex)

	def oc_release_release(self, channel, method, properties, payload):
		try:
			ref_update = json.loads(payload)
			# The routing key should ensure that we're only getting tag
			# updates
			if not ref_update['ref'].startswith('refs/tags/v'):
				raise ValueError('Not a release version tag')
			#self.queue.put(30, releasebuilder.ReleaseBuilder(self.amqp_connection, ref_update['commit'], self.log))
			return True
		except Exception, ex:
			return False, str(ex)

	@staticmethod
	def bind_to_exchange(channel, exchange, routing_key="", callback=None):
		# Create a new, anonymous queue to consume from
		queue = channel.queue_declare(exclusive=True).method.queue
		# Bind queue to exchange with the specified routing key
		channel.queue_bind(exchange=exchange, queue=queue, routing_key=routing_key)
		# Start consuming if there's a callback provided
		if callback:
			channel.basic_consume(callback, queue=queue)
		return queue

	def __call__(self):
		self.bind_to_exchange(self.amqp_channel, 'occ.ref', 'openclonk.heads.master', self.oc_release_build)
		self.bind_to_exchange(self.amqp_channel, 'occ.ref', 'openclonk.tags.*', self.oc_release_release)
		self.amqp_channel.start_consuming()
