import os
import ftptool
import posixpath
import hg
import make
import sys
import datetime

def total_seconds(td):
	return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6

class FTPHostFix(ftptool.FTPHost):

	def listdir(self,directory):
		# listdir of ftptool doesn't care for the current directory, which is an unwanted behaviour
		return ftptool.FTPHost.listdir(self, posixpath.join(self.current_directory, directory))

class DocBuilder():
	def __init__(self, revision, log):
		self.revision = revision
		self.log = log
		self.name = 'Documentation update for revision %s' % revision
	
	def __may_upload(self, name):
		return name.endswith('.html') or name.endswith('.css') or name.endswith('.js') or \
			   name.endswith('.gif') or name.endswith('.png') or name.endswith('.jpg')
	
	def __upload_new_files(self, ftphost):
		os.chdir('docs/online')
		ftphost.makedirs('/new')
		ftphost.current_directory = '/new'
		
		# note: as of python 2.7.4, os.walk('') returns nothing
		for dirpath, dirnames, filenames in os.walk('.'):
			# if uploading from windows, os.walk returns a \-style path
			dirpath = dirpath.replace('\\', '/')
			
			# create directories
			for subdir in dirnames:
				ftphost.makedirs(posixpath.join(dirpath, subdir))

			# upload files
			for filename in filenames:
				rpath = posixpath.join(dirpath, filename)
			
				if not self.__may_upload(filename):
					self.log.write('skip ' + posixpath.join(ftphost.current_directory, rpath) + '\n')
					continue

				self.log.write('upload ' + posixpath.join(ftphost.current_directory, rpath) + '\n')
				rf = ftphost.file_proxy(rpath)
				f = open(os.path.join(dirpath, filename))
				rf.upload(f)
		os.chdir('../..')
		ftphost.current_directory = ''
	
	def __replace_files(self, ftphost):
		rpaths = filter(lambda x: x != 'new', (lambda x: x[0]+x[1])(ftphost.listdir('/')))
		ftphost.makedirs('/old')
		for rpath in rpaths:
			rf = ftphost.file_proxy(posixpath.join('/', rpath))
			rf.rename(posixpath.join('/old', rpath))
		
		rpaths = (lambda x: x[0]+x[1])(ftphost.listdir('/new'))
		for rpath in rpaths:
			rf = ftphost.file_proxy(posixpath.join('/new', rpath))
			rf.rename(posixpath.join('/', rpath))
		ftphost.rmdir('/new')
	
	def __copy_old_script_files(self, ftphost):
		ftphost.current_directory = '/'
		for rdirpath, rdirnames, rfilenames in ftphost.walk(''):

			# for top level: skip 'new' folder
			if rdirpath == '':
				for rdir in rdirnames:
					if rdir == 'new':
						rdirnames.remove(rdir)
		
			# copy script files into new directory
			for rfilename in rfilenames:
				if not self.__may_upload(rfilename):
					rpath = posixpath.join(rdirpath, rfilename)
					rcopypath = posixpath.join('/new', rpath)
					self.log.write('copy ' + rpath + ' to ' + rcopypath + '\n')
					rf = ftphost.file_proxy(rpath)
					copyrf = ftphost.file_proxy(rcopypath)
					copyrf.upload_from_str(rf.download_to_str())
	
	def __remove_old_files(self, ftphost):
		ftphost.current_directory = '/old'
		rwalk = [x for x in ftphost.walk('')]
		rwalk.reverse()
		for rdirpath, rdirnames, rfilenames in rwalk:
			
			# remove directories
			for rsubdir in rdirnames:
				ftphost.rmdir(posixpath.join(rdirpath, rsubdir))

			# remove files
			for rfilename in rfilenames:
				rpath = posixpath.join(rdirpath, rfilename)
				rf = ftphost.file_proxy(rpath)
				self.log.write('delete ' + posixpath.join(ftphost.current_directory, rpath) + '\n')
				rf.delete()

		ftphost.current_directory = '/'
		ftphost.rmdir('/old')
	
	def __call__(self):
		# TODO: Exception safety
		self.log.write('updating from repository... ')
		starttime = datetime.datetime.now()
		hg.update(self.revision)
		timedelta = datetime.datetime.now() - starttime
		self.log.write('done. (took '+ str(total_seconds(timedelta)) +'s) \n')

		# Build the documentation
		self.log.write('building docs... ')
		starttime = datetime.datetime.now()
		make.make('docs')
		make.run('docs')
		timedelta = datetime.datetime.now() - starttime
		self.log.write('done. (took '+ str(total_seconds(timedelta)) +'s) \n')
		hg.revert('docs')
		
		username = 'ftp1144497-docs'
		passwd = open('../passwd/docs.txt', 'r').read().strip()
		ftphost = FTPHostFix.connect('ftp.openclonk.org', user = username, password = passwd)
		
		# upload to /new
		self.log.write('uploading new docs... \n')
		starttime = datetime.datetime.now()
		self.__upload_new_files(ftphost)
		timedelta = datetime.datetime.now() - starttime
		self.log.write('done. (took '+ str(total_seconds(timedelta)) +'s) \n')

		# copy script files over to /new
		self.log.write('copying script files... \n')
		starttime = datetime.datetime.now()
		self.__copy_old_script_files(ftphost)
		timedelta = datetime.datetime.now() - starttime
		self.log.write('done. (took '+ str(total_seconds(timedelta)) +'s) \n')
		
		# move everything in / to /old (except just uploaded new directory)
		# move everything in /new to /	
		self.log.write('replacing docs... ')
		self.__replace_files(ftphost)
		self.log.write('done. \n')
		
		# at this point, the new version is online.
		
		# delete /old folder
		# walk reverse cause the bottom-most folders need to be deleted first
		self.log.write('deleting old docs... \n')
		starttime = datetime.datetime.now()
		self.__remove_old_files(ftphost)
		timedelta = datetime.datetime.now() - starttime
		self.log.write('done. (took '+ str(total_seconds(timedelta)) +'s) \n')

		return True

#test = DocBuilder('c500d4b75c87',sys.stderr)
#test()
