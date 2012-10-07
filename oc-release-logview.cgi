import os

import logwatcher

def callback(filename, lines):
	print "data: [",
    print ','.join(lines),
	print "]"

print "Content-Type: text/event-stream\n\n"
watcher = LogWatcher(os.path.join(basedir, 'logs/oc-release.log'), callback)
watcher.loop()