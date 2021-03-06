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
	def __init__(self, amqp_connection, revision, log, build_type, dry_release):
		self.amqp_connection = amqp_connection
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
		upload_jobs = []
		for arch in arches.arches:
			date = time.strftime('%Y%m%d')
			filename = '%s-snapshot-%s-%s-%s' % (self.build_type, date, revhash[:10], arch)

			try:
				archive_stream = StringIO.StringIO()
				archive_obj = archive.Archive(arch, archive_stream)

				if arch.startswith('darwin'):
					result, uuid = autobuild.obtain(self.amqp_connection, revhash, arch, [self.build_type])
					name, stream = result[0]
					archive_obj.add(name, stream.read())
				else:
					if self.build_type == 'openclonk':
						for name, stream in contentiter.ContentIter(groupcontent.snapshot):
							archive_obj.add(name, stream.read())

					arch_iter = architer.ArchIter(self.amqp_connection, arch, revhash, self.build_type)
					for name, stream in arch_iter:
						archive_obj.add(name, stream.read())
					uuid = arch_iter.uuid

				archive_filename = archive_obj.get_filename(filename)
				archive_obj.close()
				archive_stream.seek(0)

				upload_jobs.append((archive_filename, archive_stream, uuid, arch))
			except autobuild.AutobuildException as ex:
				# make an entry for "failed build"
				archive_filename = archive_obj.get_filename(filename)
				upload_jobs.append((archive_filename, None, ex.uuid, arch))

		uploader = upload.Uploader(self.log, self.dry_release)
		for archive_filename, archive_stream, uuid, arch in upload_jobs:
			if archive_stream is not None: # Needed to skip mape osx build(?)
				uploader.nightly_file(self.build_type, archive_filename, archive_stream, uuid, revhash[:10], arch)

		return True
