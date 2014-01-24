import SimpleXMLRPCServer
import random
import hashlib
import hmac
import os

import trigger
import git
import releasebuilder

class XMLTrigger(trigger.Trigger):
	def __init__(self, queue, log):
		trigger.Trigger.__init__(self, queue, log)
		# Note we need the key path in its absolute form since the main thread
		# can change the current working directory, for example for NSIS invocation
		self.key_path = os.path.normpath(os.path.join(os.getcwd(), '../keys'))
		self.tickets = {}

	def read_key(self, user):
		return open(os.path.join(self.key_path, 'key-%s.txt' % user), 'r').read().strip()

	def consume_ticket(self, user, digest):
		if user not in self.tickets:
			raise Exception('No ticket has been issued for user %s' % user)

		ticket = self.tickets[user]
		del self.tickets[user]

		ticket_digest = hmac.new(self.read_key(user), ticket, hashlib.sha256).hexdigest()
		if ticket_digest != digest:
			raise Exception('Digest mismatch: Ticket digest is "%s", but "%s" was provided' % (ticket_digest, digest))

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
			return False, str(ex)

	def oc_release_release(self, user, digest, revision):
		try:
			self.consume_ticket(user, digest)
			self.queue.put(30, releasebuilder.ReleaseBuilder(revision, self.log))
			return True
		except Exception, ex:
			return False, str(ex)

	def __call__(self):
		server = SimpleXMLRPCServer.SimpleXMLRPCServer(('', 8000))
		server.register_function(self.oc_release_build_ticket, 'oc_release_build_ticket')
		server.register_function(self.oc_release_release, 'oc_release_release')
		server.serve_forever()
