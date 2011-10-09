import subprocess

def run(command):
	Proc = subprocess.Popen('hg %s' % command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	stdout, stderr = Proc.communicate()

	if Proc.returncode != 0:
		raise Exception('Failed to run hg command "%s":\n\n%s' % (command, stderr))

	return stdout

def clone(url):
	run('clone %s' % url)

def pull():
	run('pull')

def update(revision):
	run('update %s' % revision)

def id(url):
	return run('id')
