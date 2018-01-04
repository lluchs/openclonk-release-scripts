import threading

class FatalError(RuntimeError):
	pass

class Trigger():
	def __init__(self, queue, log):
		self.queue = queue
		self.log = log

		self.log.write('%s registering...\n' % self.__class__.__name__)

		self.thread = threading.Thread(target = self)
		self.thread.daemon = True

		self.thread.start()
		self.log.write('%s started!\n' % self.__class__.__name__)
