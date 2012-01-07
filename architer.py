import os
import re

import hg
import autobuild
import c4group

class ArchIter():
	def __init__(self, arch):
		self.arch = arch
		self.revision = hg.id() # for autobuilds
		self.index = 0

		self.files = []
		self.files.extend([
			{'type': 'autobuild', 'executable': 'clonk'},
			{'type': 'autobuild', 'executable': 'c4group'}])

		# Copy dependencies
		depdir = os.path.join('../dependencies', arch)
		try:
			dependencies = os.listdir(depdir)
		except:
			dependencies = []

		for dep in dependencies:
			self.files.append({'type': 'file', 'path':  os.path.join(depdir, dep)})

	def __iter__(self):
		 return self

	def next(self):
		if self.index == len(self.files):
			raise StopIteration()

		item = self.files[self.index]
		self.index += 1

		if item['type'] == 'file':
			filename = os.path.basename(item['path'])
			stream = open(item['path'], 'r')
		elif item['type'] == 'autobuild':
			# TODO: Make only one request for all autobuild types.
			# We could then also store UUID right from the beginning.
			result, self.uuid = autobuild.obtain(self.revision, self.arch, [item['executable']])
			filename, stream = result[0]
		else:
			raise Exception('Invalid ArchIter item type "%s"' % item['type'])

		return filename, stream
