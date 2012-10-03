import time

class Log():
	def __init__(self, filename):
		self.f = open(filename, 'w')

	def write(self, text):
		self.f.write('[%s]: %s' % (time.strftime('%c %Z'), text))
		self.f.flush()
