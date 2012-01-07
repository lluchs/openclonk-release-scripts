import threadedbuilder

class PeriodicBuilder(threadedbuilder.ThreadedBuilder):
	def __init__(self, queue, fix, interval):
		threadedbuilder.ThreadedBuilder.__init__(self, queue)

		self.fix = fix
		self.interval = interval

	def next_period(self):
		current_time = int(time.time())
		assert current_time > self.fix

		return self.interval - (current_time - self.fix) % self.interval

	def run(self):
# TODO
#		sleep(next_period())

#		self.run_periodic()
		pass

	def run_periodic(self):
		raise Exception('run_periodic() not implemented')
