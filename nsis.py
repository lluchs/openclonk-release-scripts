import subprocess

def run(source_dir, output_file, programfiles, product_name, product_company, clonk_location, c4group_location):

	command = 'makensis -NOCD -DSRCDIR=%s -DPROGRAMFILES=%s "-DPRODUCT_NAME=%s" "-DPRODUCT_COMPANY=%s" "-DCLONK=%s" "-DC4GROUP=%s" %s/tools/install/oc.nsi "-XOutFile %s"'
	command = command % (source_dir, programfiles, product_name, product_company, clonk_location, c4group_location, source_dir, output_file)

	Proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	stdout, stderr = Proc.communicate()

	if Proc.returncode != 0:
		raise Exception('Failed to run makensis: "%s":\n\n%s' % (command, stderr))

	return stdout
