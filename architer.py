import os
import re

import git
import autobuild
import c4group

import urllib
import zipfile
import StringIO

class ArchIter():
	@staticmethod
	def is_executable(filename):
		return filename.startswith('openclonk') or filename.startswith('clonk') or filename.startswith('c4group') or filename.startswith('mape')

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

			syntax_dir = 'src/mape/mape-syntax'
			for name in os.listdir(syntax_dir):
				self.files.append({'type': 'file', 'path': os.path.join(syntax_dir, name), 'directory': 'mape-syntax'})

		# Copy dependencies
		if 'win32' in arch:
			deps_dir = '%s-deps-%s' % (build_type, arch)
			dep_url = 'https://git.openclonk.org/static/autobuild/%s.zip' % deps_dir
			response = urllib.urlopen(dep_url)
			if response.getcode() != 200:
				raise Exception('Failed to download dependencies: %s' % response.read())
			responseText = response.read()
			deps = zipfile.ZipFile(file = StringIO.StringIO(responseText), mode = 'r')
			for name in deps.namelist():
				if not name.endswith('/'):
					self.files.append({'type': 'zipentry', 'obj': deps, 'path':  name, 'directory': os.path.relpath(os.path.dirname(name), deps_dir)})

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
		elif item['type'] == 'zipentry':
			if item['directory'] != '.':
				filename = item['directory'] + '/' + os.path.basename(item['path'])
			else:
				filename = os.path.basename(item['path'])
			stream = item['obj'].open(item['path'], 'r')
		elif item['type'] == 'autobuild':
			# TODO: Make only one request for all autobuild types.
			# We could then also store UUID right from the beginning.
			result, self.uuid = autobuild.obtain(self.revision, self.arch, [item['executable']])
			filename, stream = result[0]
		else:
			raise Exception('Invalid ArchIter item type "%s"' % item['type'])

		return filename, stream
