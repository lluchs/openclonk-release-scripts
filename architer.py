import os
import re

import git
import autobuild
import c4group

class ArchIter():
	@staticmethod
	def is_executable(filename):
		return filename.startswith('clonk') or filename.startswith('c4group') or filename.startswith('mape')

	def __init__(self, arch, revision):
		self.arch = arch
		self.revision = revision
		self.index = 0

		build_type = 'engine' # can be engine or mape
		self.files = []

		if build_type == 'engine':
			self.files.extend([
				{'type': 'autobuild', 'executable': 'clonk'},
				{'type': 'autobuild', 'executable': 'c4group'}])
		else:
			self.files.extend([
				{'type': 'autobuild', 'executable': 'mape'}])

		# Copy dependencies
		depdir = os.path.join('../dependencies-%s' % build_type, arch)
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
			# TODO: Take sub-directories into account properly, don't just take the file basename
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
