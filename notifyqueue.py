import Queue

class NotifyQueue():
	def __init__(self):
		self.queue = Queue.PriorityQueue()

	def put(self, priority, job):
		return self.queue.put((priority, job))

	def get(self):
		priority, job = self.queue.get()
		return job
