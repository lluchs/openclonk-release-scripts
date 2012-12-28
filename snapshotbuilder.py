import os
import time
import zipfile
import tarfile
import StringIO

import git
import arches
import autobuild
import upload
import contentiter
import architer

class SnapshotBuilder():
	def __init__(self, revision, log):
		self.revision = revision
		self.log = log
		self.name = 'Development snapshot for revision %s' % revision

	def __call__(self):
		# TODO: Exception safety
		git.reset(self.revision)
		revhash = git.id()

		# TODO: Use same content streams for all architectures
		for arch in arches.arches:
			date = time.strftime('%Y%m%d')
			filename = 'openclonk-snapshot-%s-%s-%s' % (date, revhash[:10], arch)

			# TODO: Add an archive class...
			def archive_name(basename):
				if 'win32' in arch:
					return basename + '.zip'
				else:
					return basename + '.tar.bz2'

			def open_archive(stream):
				if 'win32' in arch:
					return zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED)
				else:
					return tarfile.open(fileobj = stream, mode = 'w:bz2')

			def add_to_archive(archive, filename, content):
				if 'win32' in arch:
					archive.writestr(filename, content)
				else:
					info = tarfile.TarInfo(filename)
					if filename == 'clonk' or filename == 'c4group':
						info.mode = 0755
					else:
						info.mode = 0644
					info.mtime = time.time() # TODO: Should be the same for all files -- set once at the beginning
					info.size = len(content) # TODO: Would be cool if this could be dedcude automatically when reading the fileobj in addfile...
					archive.addfile(info, StringIO.StringIO(content))

			try:
				archive_stream = StringIO.StringIO()
				archive = open_archive(archive_stream)
				for name, stream in contentiter.ContentIter():
					add_to_archive(archive, name, stream.read())

				arch_iter = architer.ArchIter(arch)
				for name, stream in arch_iter:
					add_to_archive(archive, name, stream.read())
				uuid = arch_iter.uuid
				archive.close()

				archive_filename = archive_name(filename)
				archive_stream.seek(0)

				uploader = upload.Uploader(self.log)
				uploader.nightly_file(archive_filename, archive_stream, uuid, revhash[:10], arch)
			except autobuild.AutobuildException as ex:
				# make an entry for "failed build"
				archive_filename = archive_name(filename)
				uploader = upload.Uploader(self.log)
				uploader.nightly_file(archive_filename, None, ex.uuid, revhash[:10], arch)

		return True
