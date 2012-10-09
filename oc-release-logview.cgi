#!/usr/bin/env python
import os
import sys
import threading
import pyinotify

class LogWatch(pyinotify.ProcessEvent):
	def __init__(self, filename, n, processor):
		self.filename = filename
		self.processor = processor
		self.watch_manager = pyinotify.WatchManager()
		self.wd = self.watch_manager.add_watch(filename, pyinotify.IN_MODIFY)[filename]

		with open(self.filename, 'r') as log:
			log.seek(0, 2)
			size = log.tell()
			log.seek(-min(n * 256, size), 1)
			lines = log.read()
			self.pos = log.tell()
			self.processor([line for line in lines.split('\n') if line.strip() != ''][-n:])

	def run(self):
		notifier = pyinotify.Notifier(self.watch_manager, self)
		while True:
			try:
				if notifier.check_events(timeout=None):
					notifier.read_events()
					notifier.process_events()
			except KeyboardInterrupt:
				notifier.stop()
				break

	def process_default(self, event):
		# The watch is removed automatically after it fired,
		# so we re-add it to watch for further changes
		self.watch_manager.add_watch(self.filename, pyinotify.IN_MODIFY)
		with open(self.filename, 'r') as log:
			log.seek(self.pos)
			newlines = log.read()
			self.pos = log.tell()
			self.processor([line for line in newlines.split('\n') if line.strip() != ''])

def callback(lines):
	for line in lines:
		print "data: %s\r\n" % line
	sys.stdout.flush()

print 'Status: 200 OK'
print "Content-Type: text/event-stream\n"
sys.stdout.flush()

basedir = os.path.dirname(os.path.realpath(sys.argv[0]))
watcher = LogWatch(os.path.join(basedir, 'logs/oc-release.log'), 50, callback)
watcher.run()
