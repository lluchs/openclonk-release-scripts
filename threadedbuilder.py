import threading

class ThreadedBuilder():
	def __init__(self, queue):
		self.queue = queue

		self.thread = threading.Thread()
		self.thread.daemon = True

		self.thread.start()

	def put(priority, job):
		self.queue.put(priority, job)
