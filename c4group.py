import os
import subprocess

def run(command):
	c4group = os.path.expandvars('$HOME/bin/c4group')

	Proc = subprocess.Popen('%s %s' % (c4group, command), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	stdout, stderr = Proc.communicate()

	if Proc.returncode != 0:
		raise Exception('Failed to run c4group command "%s":\n\n%s' % (command, stderr))

	return stdout

def pack(group):
	run('%s -p' % group)

def update(update_group, old_file, new_file, comment):
	pwd = os.getcwd()
	os.chdir(os.path.dirname(old_file))
	run('%s -g %s %s %s' % (os.path.join(pwd, update_group), os.path.basename(old_file), os.path.join(pwd, new_file), comment))
	os.chdir(pwd)
