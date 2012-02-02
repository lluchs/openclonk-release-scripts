import subprocess

def run(source_dir, output_file, x64, product_name, product_company, clonk_location, c4group_location):
	if x64:
		x64_add = '-DMULTIUSER_USE_PROGRAMFILES64=1'
	else:
		x64_add = ''

	command = 'makensis -NOCD -DSRCDIR=%s %s "-DPRODUCT_NAME=%s" "-DPRODUCT_COMPANY=%s" "-DCLONK=%s" "-DC4GROUP=%s" "-X!addincludedir %s/tools/install"  %s/tools/install/oc.nsi "-XOutFile %s"'
	command = command % (source_dir, x64_add, product_name, product_company, clonk_location, c4group_location, source_dir, source_dir, output_file)
	print command

	Proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	stdout, stderr = Proc.communicate()

	if Proc.returncode != 0:
		raise Exception('Failed to run makensis: "%s":\n\n%s' % (command, stdout)) # note nsis uses stdout for error messages

	return stdout
