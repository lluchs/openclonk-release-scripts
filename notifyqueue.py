import Queue

class NotifyQueue():
	def __init__(self):
		self.queue = Queue.PriorityQueue()

	def put(priority, job):
		self.queue.put((priority, job))

	def get():
		self.queue.get()
