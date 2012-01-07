import os
import time
import urllib
import SOAPpy
import xml.dom.minidom
import StringIO
import gzip

class AutobuildException(Exception):
	def __init__(self, message, uuid):
		Exception.__init__(self, message)
		self.uuid = uuid

def download_and_extract(hrefs):
	files = []
	for bin_type in hrefs:
		href = hrefs[bin_type]

		obj = urllib.urlopen('http://hg.openclonk.org%s' % href)
		obj = StringIO.StringIO(obj.read()) # no longer needed with python 3.2...
		gzipped = gzip.GzipFile(fileobj=obj, mode='rb')

		# Rename to clonk$EXEEXT or c4group$EXEEXT
		filename, ext = os.path.splitext(href[:-3])
		filename = bin_type + ext

#		open(os.path.join(destination, filename), 'wb').write(gzipped.read()) # I seem to remember there was a more elegant method to this but I don't find it anymore :( TODO: hm... shutil.copyfileobj?
#		os.chmod(os.path.join(destination, filename), 0755)

		files.append((filename, gzipped))
	return files

def firstElement(node):
	child = node.firstChild
	while child is not None and child.nodeType != xml.dom.Node.ELEMENT_NODE:
		child = child.nextSibling
	return child

def obtain_impl(revision, arch, binaries, have_queued):
	url = 'http://hg.openclonk.org/openclonk/xml-autobuild/%s' % revision

	reply = urllib.urlopen(url).read()
	tree = xml.dom.minidom.parseString(reply)
	toplevel = firstElement(tree)

	if toplevel.nodeName != 'autobuildlist': raise Exception('Invalid XML: Toplevel node is not "autobuildlist" but "%s"' % tree.firstChild.nodeName)
	if firstElement(toplevel).nodeName != 'changeset': raise Exception('Invalid XML: No changesets available')

	for child in firstElement(toplevel).childNodes:
		if child.nodeType != xml.dom.Node.ELEMENT_NODE: continue

		if child.nodeName == 'builds':
			for subchild in child.childNodes:
				if subchild.nodeType != xml.dom.Node.ELEMENT_NODE: continue

				if subchild.nodeName == 'build' and subchild.getAttribute('triplet') == arch:
					if subchild.getAttribute('result') == 'nobuild':
						if not have_queued:
#							self.log.write('Build for architecture %s is not available (rev %s)\n' % (arch, revision))
#							self.log.write('Queuing a build...\n')
#							server = SOAPpy.SOAPProxy('http://[2a01:238:43e1:7e01:216:3eff:fefa:d5]:32000/')
							server = SOAPpy.SOAPProxy('http://hg.openclonk.org:32000/')
							result = server.queuebuild(revision, arch)
#							self.log.write('   => %s\n' % result.strip())
							print '  =>', result

#						self.log.write('Waiting for the build to finish...\n')
						time.sleep(60)
						return obtain_impl(revision, arch, binaries, True)
					elif subchild.getAttribute('result') == 'inprogress':
#						self.log.write('Waiting for the build to finish...\n')
						time.sleep(60)
						return obtain_impl(revision, arch, binaries, True)
					elif subchild.getAttribute('result') == 'failure':
						raise AutobuildException('The build resulted in failure for architecture %s' % arch, subchild.getAttribute('uuid'))
					elif subchild.getAttribute('result') == 'success':
#						self.log.write('Build for architecture %s is available\n' % arch)

						for subsubchild in subchild.childNodes:
							if subsubchild.nodeType != xml.dom.Node.ELEMENT_NODE: continue

							if subsubchild.nodeName == 'binaries':
								hrefs = {}
								for binary in subsubchild.childNodes:
									if binary.nodeType != xml.dom.Node.ELEMENT_NODE: continue

									if binary.nodeName == 'binary':
										bin_type = binary.getAttribute('type')
										if bin_type in map(lambda x: 'make: ' + x, binaries):
											hrefs[bin_type[6:]] = binary.getAttribute('href')
								if len(hrefs) != len(binaries):
									raise Exception('Autobuilder did not build all requested binaries')

								return download_and_extract(hrefs), subchild.getAttribute('uuid')
						else:
#							return ([], subchild.getAttribute('uuid'))
							raise AutobuildException('No binaries available for successful build of architecture %s' % arch, subchild.getAttribute('uuid'))
					else:
							raise AutobuildException('Unexpected build result "%s" for revision %s, architecture %s' % (subchild.getAttribute('result'), revision, arch), subchild.getAttribute('uuid'))
			else:
				raise Exception('Autobuilder has no build for architecture %s available' % arch)
	else:
		raise Exception('Invalid XML: Changeset has no builds')

def obtain(revision, arch, binaries):
	return obtain_impl(revision, arch, binaries, False)
