import subprocess

def run(command):
	Proc = subprocess.Popen('make %s' % command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	stdout, stderr = Proc.communicate()

	if Proc.returncode != 0:
		raise Exception('Failed to run make %s:\n\n%s' % (command, stderr))

	return stdout

def make(directory):
	run('-C %s' % directory)
