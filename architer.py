import os
import re

import git
import autobuild
import c4group

class ArchIter():
	@staticmethod
	def is_executable(filename):
		return filename.startswith('openclonk') or filename.startswith('c4group') or filename.startswith('mape')

	def __init__(self, arch, revision, build_type):
		self.arch = arch
		self.revision = revision
		self.index = 0

		self.files = []

		if build_type == 'openclonk':
			self.files.extend([
				{'type': 'autobuild', 'executable': 'openclonk'},
				{'type': 'autobuild', 'executable': 'c4group'}])
		else:
			self.files.extend([
				{'type': 'autobuild', 'executable': 'mape'}])

		# Copy dependencies
		depdir = os.path.join('../dependencies-%s' % build_type, arch)
		try:
			dependencies = os.walk(depdir)
		except:
			dependencies = []

		for dirpath, dirnames, filenames in dependencies:
			for filename in filenames:
				self.files.append({'type': 'file', 'path':  os.path.join(dirpath, filename), 'directory': os.path.relpath(dirpath, depdir)})

	def __iter__(self):
		 return self

	def next(self):
		if self.index == len(self.files):
			raise StopIteration()

		item = self.files[self.index]
		self.index += 1

		if item['type'] == 'file':
			# TODO: Take sub-directories into account properly, don't just take the file basename
			if item['directory'] != '.':
				filename = item['directory'] + '/' + os.path.basename(item['path'])
			else:
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
