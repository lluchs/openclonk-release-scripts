import os
import time
import urllib
import SOAPpy
import xml.dom.minidom
import StringIO
import gzip
import json
from backports import lzma

class AutobuildException(Exception):
	def __init__(self, message, uuid):
		Exception.__init__(self, message)
		self.uuid = uuid

def download_and_extract(hrefs):
	files = []
	for bin_type in hrefs:
		href = hrefs[bin_type]

		obj = urllib.urlopen('http://git.openclonk.org%s' % href)
		obj = StringIO.StringIO(obj.read()) # no longer needed with python 3.2, but then we need to find a way to guess the file type

		# Guess file type
		magic_dict = {
			"\x1f\x8b\x08": lambda x: gzip.GzipFile(fileobj=x, mode='rb'),
			"\xfd\x37\x7a\x58\x5a\x00": lambda x: lzma.LZMAFile(x, mode='rb'),
			"\x50\x4b\x03\x04": lambda x: x # .zip
		}

		max_magic = max(len(x) for x in magic_dict)
		file_start = obj.read(max_magic)
		obj.seek(0)

		zipped = None
		for magic, ctor in magic_dict.items():
			if file_start.startswith(magic):
				zipped = ctor(obj)
				break;

		if zipped is None:
			raise Exception('File type not recognized')
	
		# Rename to clonk$EXEEXT or c4group$EXEEXT
		filename, ext = os.path.splitext(href[:-3])
		filename = bin_type + ext

		files.append((filename, zipped))
	return files

def firstElement(node):
	child = node.firstChild
	while child is not None and child.nodeType != xml.dom.Node.ELEMENT_NODE:
		child = child.nextSibling
	return child

def obtain_impl(amqp_connection, revision, arch, binaries, have_queued):
	url = 'http://git.openclonk.org/openclonk/xml-autobuild/%s' % revision

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
							message = json.dumps({'type': 'enqueue', 'project': 'openclonk', 'commit': revision})
							amqp_channel = amqp_connection.channel()
							amqp_channel.basic_publish(exchange='', routing_key='ocbuild.control', body=message)

#						self.log.write('Waiting for the build to finish...\n')
						time.sleep(60)
						return obtain_impl(amqp_connection, revision, arch, binaries, True)
					elif subchild.getAttribute('result') == 'inprogress' or subchild.getAttribute('result') == 'enqueued':
#						self.log.write('Waiting for the build to finish...\n')
						time.sleep(60)
						return obtain_impl(amqp_connection, revision, arch, binaries, True)
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
										tmp_binaries = binaries[:]
										if 'openclonk' in tmp_binaries: tmp_binaries.append('clonk') # backwards compatibility
										if bin_type in map(lambda x: 'make: ' + x, tmp_binaries):
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

def obtain(amqp_connection, revision, arch, binaries):
	return obtain_impl(amqp_connection, revision, arch, binaries, False)
