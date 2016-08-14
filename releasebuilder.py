import errno
import os
import re
import shutil
import tarfile

import git
import autobuild
import arches
import groupcontent
import c4group
import contentiter
import architer
import nsis
import upload

def _ensure_dir_exists(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

def _create_and_open(path):
    """Create directories to the given path if they don't exist,
    then open the file for writing."""
    _ensure_dir_exists(os.path.dirname(path))
    return open(path, 'w')

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
			nsis.run(pwd, '../' + basename, '-amd64-' in arch, items['C4ENGINENAME'], items['C4PROJECT'], engine_executable_name, 'c4group.exe')
			os.chdir(pwd)

			shutil.rmtree(directory)
			return os.path.join(os.path.dirname(directory), basename)
		elif arch.startswith('darwin'):
			basename += '.app.zip'
			outname = os.path.join(os.path.dirname(directory), basename)
			zipfile = [x for x in os.listdir(directory) if x.endswith('.zip')][0]
			shutil.copy(os.path.join(directory, zipfile), outname)
			return outname
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
		if not self.revision.startswith('v'):
			for x in 'ghijklmnopqrstuvwxyz':
				if len(prefix) == 0 and x in self.revision:
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
			_create_and_open(destination).write(stream.read()) # TODO: copyfileobj?

		# Create architecture specific files:
		all_files = {}
		for arch in arches.arches:
			# Obtain clonk and c4group binaries and dependencies and save in archive/$arch
			self.log.write('Creating architecture dependent files for %s...\n' % arch)

			archdir = os.path.join(archive, arch)
			os.mkdir(archdir)

			binaries = []
			if arch.startswith('darwin'):
				result, uuid = autobuild.obtain(self.amqp_connection, revision, arch, ['openclonk'])
				filename, stream = result[0]
				_create_and_open(os.path.join(archdir, filename)).write(stream.read())
				binaries.append(filename)
			else:
				# Copy both binaries and dependencies into archive. 
				for filename, stream in architer.ArchIter(self.amqp_connection, arch, revision, 'openclonk'):
					_create_and_open(os.path.join(archdir, filename)).write(stream.read())
					if architer.ArchIter.is_executable(filename):
						os.chmod(os.path.join(archdir, filename), 0755)
					binaries.append(filename)

			# Create distribution directory and copy both common and
			# architecture dependent files there.
			distdir = os.path.join(archdir, 'openclonk-%d.%d' % (major, minor))
			os.mkdir(distdir)
			if not arch.startswith('darwin'):
				for filename in content + others:
					_ensure_dir_exists(os.path.dirname(os.path.join(distdir, filename)))
					shutil.copy(os.path.join(archive, filename), os.path.join(distdir, filename))
			for filename in binaries:
				_ensure_dir_exists(os.path.dirname(os.path.join(distdir, filename)))
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
