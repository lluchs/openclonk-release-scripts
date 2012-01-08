import SimpleXMLRPCServer
import random
import hashlib
import hmac
import os

import trigger
import hg
import snapshotbuilder

class RevisionPushed():
	def __init__(self, queue, log):
		self.queue = queue
		self.log = log

	def __call__(self):
		self.log.write('New changesets have been pushed.\n')

		# See if the push changed something in the default branch
		hg.update('default')
		current_id = hg.id()
		hg.pull()
		hg.update('default')
		new_id = hg.id()

		if current_id != new_id:
			self.log.write('The default branch has new changesets.\n')

			# Make a new development snapshot
			builder = snapshotbuilder.SnapshotBuilder(new_id, self.log)
			# TODO: Remove all other snapshot builders from the queue
			self.queue.put(95, builder)
		else:
			self.log.write('The default branch has no new changesets.\n')

		# TODO: Make a release if the version changed

		return True

class PushTrigger(trigger.Trigger):
	def __init__(self, queue, log):
		trigger.Trigger.__init__(self, queue, log)
		# Note we need the key path in its absolute form since the main thread
		# can change the current working directory, for example for NSIS invocation
		self.key_path = os.path.normpath(os.path.join(os.getcwd(), '../keys'))
		self.tickets = {}

	def read_key(self, user):
		return open(os.path.join(self.key_path, 'key-%s.txt' % user), 'r').read().strip()

	def oc_release_build_ticket(self, user):
		try:
			# We don't need the key here, but this throws an
			# exception if we do not know the given user, not
			# issuing a ticket at all in this case.
			key = self.read_key(user)

			ticket = ''.join(map(lambda x: "%c" % random.randrange(32, 128), [0]*random.randint(10,16)))

			# TODO: Ticket expiry
			self.tickets[str(user)] = ticket

			return ticket
		except Exception, ex:
			print ex
			return False


	def oc_release_build(self, user, digest):
		try:
			if user not in self.tickets:
				raise Exception('No ticket has been issued for user %s' % user)

			ticket = self.tickets[user]
			del self.tickets[user]

			ticket_digest = hmac.new(self.read_key(user), ticket, hashlib.sha256).hexdigest()
			if ticket_digest != digest:
				raise Exception('Digest mismatch: Ticket digest is "%s", but "%s" was provided' % (ticket_digest, digest))

			# High priority to handle this revision push, it
			# will then queue the actual builders after
			# examining the nature of the new commits.
			self.queue.put(0, RevisionPushed(self.queue, self.log))
			return True
		except Exception, ex:
			print ex
			return False

	def __call__(self):
		server = SimpleXMLRPCServer.SimpleXMLRPCServer(('', 8000))
		server.register_function(self.oc_release_build_ticket, 'oc_release_build_ticket')
		server.register_function(self.oc_release_build, 'oc_release_build')
		server.serve_forever()
