import os
import re
import c4group

class ContentIter():
	@staticmethod
	def is_group_file(filename):
		if re.match('.*\\.oc[fgd]', filename): return True
		return False
		
	def __init__(self, groupfiles):
		self.index = 0

		# Add game content files
		self.files = map(lambda x: os.path.join('planet', x), groupfiles)

		# Add misc other files which are architecture independent
		self.files.extend([
			'planet/AUTHORS',
			'planet/COPYING',
			'Credits.txt',
			'licenses/LGPL.txt'
		])

	def __iter__(self):
		 return self

	def next(self):
		if self.index == len(self.files):
			raise StopIteration()

		filename = self.files[self.index]
		self.index += 1

		# If it is a group, move to /tmp, pack and return. We cannot
		# stream with c4group yet :(
		if ContentIter.is_group_file(os.path.basename(filename)):
			tmp_filename = os.path.join('/tmp', os.path.basename(filename))
			c4group.packto(filename, tmp_filename)
			stream = open(tmp_filename, 'r')
			os.unlink(tmp_filename)
		else:
			stream = open(filename, 'r')

		return os.path.basename(filename), stream
