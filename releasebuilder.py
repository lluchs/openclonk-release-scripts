import os
import re
import shutil
import tarfile

import git
import arches
import groupcontent
import c4group
import contentiter
import architer
import nsis
import upload

class ReleaseBuilder():
	def __init__(self, amqp_connection, revision, log, dry_release):
		self.amqp_connection = amqp_connection
		self.archive_dir = '../release-archive'
		self.revision = revision
		self.log = log
		self.dry_release = dry_release

		# TODO: Cannot parse version file at this point yet - might
		# want to take as constructor params.
		self.name = 'Release for revision %s' % revision

	def parse_version_file(self, filename):
		v = [-1,-1]
		for line in open(filename, 'r'):
			match = re.match('SET\\(C4XVER([1-2])\\s+([0-9]+)\\)', line)
			if match is not None:
				v[int(match.group(1))-1] = int(match.group(2))

		if -1 in v:
			raise Exception('Failed to parse version number')

		return v[0], v[1]

	# The given directory contains all distribution files. This packs it into
	# whatever is appropriate for arch: Windows installer or a tarball
	# Returns the name.
	def pack_full_installation(self, directory, arch):
		basename = os.path.basename(directory)
		if '-amd64-' in arch:
			basename += '-x64'

		if arch.startswith('win32'):
			basename += '.exe'
			#exename = os.path.join(os.path.dirname(directory), basename)

			# Read Version.txt
			items = {}
			for line in open('Version.txt', 'r'):
				match = re.match('SET\\(([A-Z0-9]+)\s+"(.*)"\\)', line)
				if match:
					items[match.group(1)] = match.group(2)

			# This gets its AUTHORS, COPYING, etc. from a
			# different location but that's OK for now
			pwd = os.getcwd()
			os.chdir(directory)

			engine_executable_name = 'openclonk.exe'
			nsis.run(pwd, '../' + basename, '-amd64-' in arch, items['C4ENGINENAME'] + items['C4VERSIONBUILDNAME'], items['C4PROJECT'], engine_executable_name, 'c4group.exe')
			os.chdir(pwd)

			shutil.rmtree(directory)
			return os.path.join(os.path.dirname(directory), basename)
		else:
			basename += '.tar.bz2'
			tarname = os.path.join(os.path.dirname(directory), basename)
			tar = tarfile.open(tarname, 'w:bz2')
			tar.add(directory, os.path.basename(directory))
			tar.close()
			shutil.rmtree(directory)
			return tarname

	# TODO: Make this use smaller chunks, and proper cleanup in error cases (try/finally)
	def __call__(self):
		if self.dry_release:
			self.log.write('Dry-Releasing revision %s...\n' % self.revision)
		else:
			self.log.write('Releasing revision %s...\n' % self.revision)

		# Update to revision and get hexadecimal ID.
		# TODO: Reset back to 'origin/master' afterwards

		# TODO: The following could be checked easier maybe...
		prefix = ''
		for x in 'ghijklmnopqrstuvwxyz':
			if len(prefix) == 0:
				prefix = 'origin/'

		git.fetch()
		git.reset('%s%s' % (prefix, self.revision))
		revision = git.id()[:12]

		(major, minor) = self.parse_version_file('Version.txt')

		self.log.write('==> Version %d.%d\n' % (major, minor))

		dry_suffix = ''
		if self.dry_release: dry_suffix = '-dry'
		archive = os.path.join(self.archive_dir, '%d.%d%s' % (major, minor, dry_suffix))

		if os.path.exists(archive):
			self.log.write('Archive directory %s exists already. Clearing...\n' % archive)
			shutil.rmtree(archive)

		os.mkdir(archive)

		# Copy game content to archive
		self.log.write('Copying and packing game content to archive...\n')
		content = [] # game content
		others  = [] # other misc. non-architecture dependent files
		for filename, stream in contentiter.ContentIter(groupcontent.release):
			self.log.write('%s...\n' % filename)
			if contentiter.ContentIter.is_group_file(filename):
				content.append(filename)
			else:
				others.append(filename)

			destination = os.path.join(archive, filename)
			open(destination, 'w').write(stream.read()) # TODO: copyfileobj?

		# Create architecture specific files:
		all_files = {}
		for arch in arches.arches:
			# Obtain clonk and c4group binaries and dependencies and save in archive/$arch
			self.log.write('Creating architecture dependent files for %s...\n' % arch)

			archdir = os.path.join(archive, arch)
			os.mkdir(archdir)

			# Copy both binaries and dependencies into archive. 
			binaries = []
			for filename, stream in architer.ArchIter(self.amqp_connection, arch, revision, 'openclonk'):
				open(os.path.join(archdir, filename), 'w').write(stream.read())
				if architer.ArchIter.is_executable(filename):
					os.chmod(os.path.join(archdir, filename), 0755)
				binaries.append(filename)

			# Create distribution directory and copy both common and
			# architecture dependent files there.
			distdir = os.path.join(archdir, 'openclonk-%d.%d' % (major, minor))
			os.mkdir(distdir)
			for filename in content + others:
				shutil.copy(os.path.join(archive, filename), os.path.join(distdir, filename))
			for filename in binaries:
				shutil.copy(os.path.join(archdir, filename), os.path.join(distdir, filename))

			# Create full installation package
			file = self.pack_full_installation(distdir, arch)
			all_files[arch] = file

		# TODO: Create a source tarball

		uploader = upload.Uploader(self.log, self.dry_release)
		
		# TODO uncomment when source tarball created
		#uploader.release_file(source_package_filename, (major, minor))
		
		for arch,file in all_files.items():
			uploader.release_binaries(file, arch, (major, minor))
			os.unlink(file)

		# Remove the archive if this was a dry release
		if self.dry_release:
			shutil.rmtree(archive)
		return True
