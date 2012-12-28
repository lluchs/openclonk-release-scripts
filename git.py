import subprocess

def run(command):
	Proc = subprocess.Popen('git %s' % command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	stdout, stderr = Proc.communicate()

	if Proc.returncode != 0:
		raise Exception('Failed to run git command "%s":\n\n%s' % (command, stderr))

	return stdout

def clone(url):
	run('clone %s' % url)

def fetch():
	run('fetch')

def reset(revision):
	run('reset --hard %s' % revision)

def id():
	return run('rev-parse HEAD').strip()

def log(directory, current_id, new_id, pretty):
	return run('log %s..%s --pretty=%s %s' % (current_id, new_id, pretty, directory)).strip()
