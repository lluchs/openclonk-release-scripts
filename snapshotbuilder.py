import os
import time
import StringIO

import git
import arches
import groupcontent
import archive
import autobuild
import upload
import contentiter
import architer

class SnapshotBuilder():
	def __init__(self, revision, log, build_type, dry_release):
		self.revision = revision
		self.log = log
		self.build_type = build_type
		self.dry_release = dry_release

		self.name = '%s Development snapshot for revision %s' % (build_type, revision)

	def __call__(self):
		# TODO: Exception safety
		# TODO: If a branch name is given, checkout the branch from remote
		# TODO: Reset back to 'origin/master' afterwards
		git.reset(self.revision)
		revhash = git.id()

		# TODO: Use same content streams for all architectures
		for arch in arches.arches:
			date = time.strftime('%Y%m%d')
			filename = '%s-snapshot-%s-%s-%s' % (self.build_type, date, revhash[:10], arch)

			try:
				#macbuilder = macbuilder.MacBuilder(revhash) # autobuilder in other cases

				archive_stream = StringIO.StringIO()
				archive_obj = archive.Archive(arch, archive_stream)

				if self.build_type == 'openclonk':
					for name, stream in contentiter.ContentIter(groupcontent.snapshot):
						archive_obj.add(name, stream.read())

				arch_iter = architer.ArchIter(arch, revhash, self.build_type)
				for name, stream in arch_iter:
					archive_obj.add(name, stream.read())

				archive_filename = archive_obj.get_filename(filename)
				archive_obj.close()
				archive_stream.seek(0)

				uuid = arch_iter.uuid
				uploader = upload.Uploader(self.log, self.dry_release)
				uploader.nightly_file(self.build_type, archive_filename, archive_stream, uuid, revhash[:10], arch)
			except autobuild.AutobuildException as ex:
				# make an entry for "failed build"
				archive_filename = archive_obj.get_filename(filename)
				uploader = upload.Uploader(self.log, self.dry_release)
				uploader.nightly_file(self.build_type, archive_filename, None, ex.uuid, revhash[:10], arch)

		return True
