import os
import re
import shutil
import tarfile

import git
import arches
import c4group
import contentiter
import architer
import nsis
import upload

class ReleaseBuilder():
	def __init__(self, revision, log):
		self.archive_dir = '../release-archive'
		self.revision = revision
		self.log = log

		# TODO: Cannot parse version file at this point yet - might
		# want to take as constructor params.
		self.name = 'Release for revision %s' % revision

	def parse_version_file(self, filename):
		v = [-1,-1,-1]
		for line in open(filename, 'r'):
			match = re.match('SET\\(C4XVER([1-3])\\s+([0-9]+)\\)', line)
			if match is not None:
				v[int(match.group(1))-1] = int(match.group(2))

		if -1 in v:
			raise Exception('Failed to parse version number')

		return v[0], v[1], v[2]

	def parse_version_number(self, line):
		match = re.match('([0-9]+)\\.([0-9]+)\\.([0-9]+)', line)
		if not match:
			raise Exception('Invalid version number: %s' % line)
		return int(match.group(1)), int(match.group(2)), int(match.group(3))

	def can_update(self, (major1, minor1, micro1), (major2, minor2, micro2)):
		# We cannot update between major versions
		if major1 != major2: return False

		# We don't do downgrades
		if minor1 > minor2: return False

		# When a new minor release is made then we generate update
		# from all of the previous release series
		if micro2 == 0: return minor1 == minor2 - 1

		# For a new micro release we generate updates for all previous
		# releases in the same series.
		return micro1 < micro2

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

			# For backward compatibility
			engine_executable_name = 'openclonk.exe'
			if os.path.exists('clonk.exe'):
				engine_executable_name = 'clonk.exe'
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
		dry_release = False

		if dry_release:
			self.log.write('Dry-Releasing revision %s...\n' % self.revision)
		else:
			self.log.write('Releasing revision %s...\n' % self.revision)

		# Update to revision and get hexadecimal ID.
		# TODO: If a branch name is given, checkout the branch from remote
		# TODO: Reset back to 'origin/master' afterwards
		git.fetch()
		git.reset(self.revision)
		revision = git.id()[:12]

		(major, minor, micro) = self.parse_version_file('Version.txt')

		self.log.write('==> Version %d.%d.%d\n' % (major, minor, micro))

		dry_suffix = ''
		if dry_release: dry_suffix = '-dry'
		archive = os.path.join(self.archive_dir, '%d.%d.%d%s' % (major, minor, micro, dry_suffix))

		if os.path.exists(archive):
			self.log.write('Archive directory %s exists already. Clearing...\n' % archive)
			shutil.rmtree(archive)

		available_versions = filter(lambda x: not x.startswith('.'), os.listdir(self.archive_dir))
		os.mkdir(archive)

		# Copy game content to archive
		self.log.write('Copying and packing game content to archive...\n')
		content = [] # game content
		others  = [] # other misc. non-architecture dependent files
		for filename, stream in contentiter.ContentIter():
			self.log.write('%s...\n' % filename)
			if contentiter.ContentIter.is_content_file(filename):
				content.append(filename)
			else:
				others.append(filename)

			destination = os.path.join(archive, filename)
			open(destination, 'w').write(stream.read()) # TODO: copyfileobj?

		# Create content update
		old_versions = filter(lambda x: self.can_update(x, (major, minor, micro)), map(lambda x: self.parse_version_number(x), available_versions))
		supported_versions = []

		if len(old_versions) > 0:
			self.log.write('Old versions found: %s\n' % str(old_versions))
			self.log.write('Creating content update...\n')

			# Create update folder
			update = os.path.join(archive, 'Update.ocu')
			os.mkdir(update)
			open(os.path.join(update, 'AutoUpdate.txt'), 'w').write("")

			# Run through old versions
			for old_major,old_minor,old_micro in old_versions:
				self.log.write('Creating update from version %d.%d.%d...\n' % (old_major, old_minor, old_micro))
				old_archive = os.path.join(self.archive_dir, '%d.%d.%d' % (old_major, old_minor, old_micro))
				old_files = filter(lambda x: contentiter.ContentIter.is_content_file(x), os.listdir(old_archive))

				# Check that all previous files are available
				# in the current version. C4Update does not
				# support removing files between versions.
				have_all_content = True
				for filename in old_files:
					if not filename in content:
						have_all_content = False
						break

				if not have_all_content:
					self.log.write('Cannot update from version %d.%d.%d because files have been removed.\n' % (old_major, old_minor, old_micro))
					continue

				supported_versions.append((old_major, old_minor, old_micro))
				for filename in content:
					update_filename = filename + '.ocu'
					update_path = os.path.join(update, update_filename)
					if not filename in content:
						# A new top-level file was created in the current version that
						# did not yet exist in the previous version.
						# Add the full file to the update group and remove
						# the incremental update for it, if any.
						if os.path.exists(update_path):
							shutil.rmtree(update_path)
						shutil.copy(os.path.join(archive, filename), os.path.join(update, filename))
					else:
						# The file is available. Make sure .oc? does not exist and then do the update
						if not os.path.exists(os.path.join(update, filename)):
							c4group.update(update_path, os.path.join(old_archive, filename), os.path.join(archive, filename), '%d.%d.%d' % (major, minor, micro))

				for filename in others:
					old_arch = os.path.join(self.archive_dir, '%d.%d.%d' % (old_major, old_minor, old_micro))
					old_path = os.path.join(old_arch, filename)
					new_path = os.path.join(archive, filename)
					if not os.path.exists(old_path) or open(old_path, 'rb').read() != open(new_path, 'rb').read():
						shutil.copy(new_path, os.path.join(update, filename))
						break

		# Create architecture specific files:
		all_files = {}
		for arch in arches.arches:
			# Obtain clonk and c4group binaries and dependencies and save in archive/$arch
			self.log.write('Creating architecture dependent files for %s...\n' % arch)

			archdir = os.path.join(archive, arch)
			os.mkdir(archdir)

			# Copy both binaries and dependencies into archive. 
			binaries = []
			for filename, stream in architer.ArchIter(arch, revision, 'openclonk'):
				open(os.path.join(archdir, filename), 'w').write(stream.read())
				if architer.ArchIter.is_executable(filename):
					os.chmod(os.path.join(archdir, filename), 0755)
				binaries.append(filename)

			# Create distribution directory and copy both commond and
			# architecture dependent files there.
			distdir = os.path.join(archdir, 'openclonk-%d.%d.%d' % (major, minor, micro))
			os.mkdir(distdir)
			for filename in content + others:
				shutil.copy(os.path.join(archive, filename), os.path.join(distdir, filename))
			for filename in binaries:
				shutil.copy(os.path.join(archdir, filename), os.path.join(distdir, filename))

			# Create full installation package
			full_file = self.pack_full_installation(distdir, arch)
			all_files[arch] = { 'full': full_file }

			# Some old_versions might not be available for this architecture, for example in case the architecture was only added
			# at some later point to the build process.
			arch_old_versions = []
			for old_major,old_minor,old_micro in supported_versions:
				old_arch = os.path.join(self.archive_dir, '%d.%d.%d' % (old_major, old_minor, old_micro), arch)
				# If this does not exist then we cannot update from this version. The content update has already
				# been created, so the update for this arch might be a bit bigger than it would have to be. But
				# this case should not happen anyway so we are OK.
				if os.path.exists(old_arch):
					arch_old_versions.append((old_major, old_minor, old_micro))
				else:
					self.log.write('Discarding old version %d.%d.%d from update for architecture %s.\n' % (old_major, old_minor, old_micro, arch))

			all_files[arch]['old_versions'] = arch_old_versions[:]

			# Copy arch files into update
			if len(arch_old_versions) > 0:
				# Note that we do not abort the update if a depedency file is removed. Even
				# though C4Update cannot handle this it shouldn't hurt if the unused file
				# stays around in the Clonk directory.

				dist_update = os.path.join(archdir, 'openclonk-%d.%d.%d-%s.ocu' % (major, minor, micro, arch))
				shutil.copytree(update, dist_update)

				for filename in binaries:
					for old_major,old_minor,old_micro in arch_old_versions:
						old_arch = os.path.join(self.archive_dir, '%d.%d.%d' % (old_major, old_minor, old_micro), arch)
						old_path = os.path.join(old_arch, filename)
						new_path = os.path.join(archdir, filename)
						if not os.path.exists(old_path) or open(old_path, 'rb').read() != open(new_path, 'rb').read():
							shutil.copy(new_path, os.path.join(dist_update, filename))
							break

				c4group.pack(dist_update)
				all_files[arch]['update'] = dist_update

		if len(old_versions) > 0:
			shutil.rmtree(update)

		# TODO: Create a source tarball

		uploader = upload.Uploader(self.log, dry_release)
		
		# TODO uncomment when source tarball created
		#uploader.release_file(source_package_filename, (major, minor, micro))
		
		for arch in all_files:
			files = all_files[arch]
			assert 'full' in files

			uploader.release_binaries(files['full'], arch, (major, minor, micro), [])
			os.unlink(files['full'])

			if 'update' in files:
				uploader.release_binaries(files['update'], arch, (major, minor, micro), files['old_versions'])
				os.unlink(files['update'])

		# Remove the archive if this was a dry release
		if dry_release:
			shutil.rmtree(archive)
		return True
