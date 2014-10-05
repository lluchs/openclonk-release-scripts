#!/usr/bin/env python
import os
import re
import sys

import xmlrpclib
import hmac
import hashlib
import urllib

# config:
user_blacklist = ['boom']

# startup:
basedir = os.path.dirname(os.path.realpath(sys.argv[0]))
users = sorted([user[4:-4] for user in os.listdir(os.path.join(basedir, '../keys')) if user.startswith('key-') and user.endswith('.txt') and user[4:-4] not in user_blacklist])
action = sys.stdin.read()

# action / XMLRPC
message_type = 'MessageSuccess'
message_text = ''

try:
	params = action.split('&')
	param_map = {}
	for param in params:
		if param.strip() != '':
			[key, value] = param.split('=')
			param_map[key] = value

	if 'submit_release' in param_map:
		user = urllib.unquote(param_map['user'])
		passphrase = urllib.unquote(param_map['passphrase'])
		revision = urllib.unquote(param_map['revision'])
		dry_release = 'dry_release' in param_map

		if passphrase.strip() == '': raise Exception('Empty passphrase')
		if revision.strip() == '': raise Exception('Empty revision')

		proxy = xmlrpclib.ServerProxy('http://localhost:8000')
		ticket = proxy.oc_release_build_ticket(user)
		if type(ticket) != str: raise Exception('No such user')

		digest = hmac.new(passphrase.strip(), ticket, hashlib.sha256).hexdigest()
		result = proxy.oc_release_release(user, digest, revision, dry_release)
		if result != True: raise Exception('Not authorized')

		message_type = 'MessageSuccess'
		message_text = 'Release scheduled.'

except Exception, ex:
	message_type = 'MessageError'
	message_text = str(ex)

# Output
print 'Status: 200 OK'
print 'Content-Type: text/html'
print ''

print """
<html>
 <head>
  <title>OC Release Interface</title>

  <style type="text/css">
   html {
     font-size: 12px;
     font-family: Arial, Sans Serif;
   }
   
   ul li {
     padding: 8px 0;
     line-height: 150%%;
   }
  
   #Form {
     background: black url(redbutton.jpg) no-repeat left top;
     width: 269px;
     height: 400px;
     float: left;
     margin: 20px;
   }
   
   #Inputs {
     height: 130px;
     padding: 20px 20px;
     color: white;
     font-weight: bold;
     text-align: center;
   }
   
   #Inputs label {
     display:block;
   }
   
   #Inputs input, #Inputs select {
     margin: 2px 0 8px 0;
     width: 140px;
     border: 1px solid grey;
   }

   #Inputs #DryRelease {
     width: 20px;
   }
   
   #SubmitButton {
     position: relative;
     top: 65px;
     left: 84px;
     width: 106px;
     height: 106px;
     border: 0;
     background-color: transparent;
     color: transparent;
   }
   
   #SubmitButton:hover {
     background: url(redbutton_hl.jpg) no-repeat left top;
   }
   
   #Checklist {
     float: left;
     margin: 20px;
   }
   
   #Log {
     clear:both;
   }
   
   #LogBody {
     font-family: Courier, monospace;
   }

   span.MessageSuccess {
     padding-left: 5px;
     padding-right: 5px;
     color: #FFFFFF;
     background-color: #088A08;
     font-weight: bold;
   }

   span.MessageError {
     padding-left: 5px;
     padding-right: 5px;
     color: #FFFFFF;
     background-color: #8A0808;
     font-weight: bold;
   }
  </style>
  <script type="text/javascript">
    var evtSource = new EventSource("oc-release-logview.cgi");
    evtSource.onmessage = function(e) {
      var txt = document.createTextNode(e.data);
      if(document.getElementById('LogBody').innerHTML != "")
        document.getElementById('LogBody').appendChild(document.createElement('br'));
      document.getElementById('LogBody').appendChild(txt); 
    }
    evtSource.onopen = function(e) {
      document.getElementById('LogBody').innerHTML = "";
    }
  </script>
 </head>

 <body>
   <div id="Form">
     <form action="%(target)s" method="POST">
      <div id="Inputs">
        <label for="User">User</label>
        <select id="User" name="user">
         %(userlist)s
        </select>
        <label for="Passphrase">Passphrase</label>
        <input id="Passphrase" name="passphrase" type="text" required="required"/>
        <label for="Revision">Changeset ID or branch name</label>
        <input id="Revision" name="revision" type="text" required="required"/><br />
        <input id="DryRelease" name="dry_release" type="checkbox" checked="checked" />Dry Release
      </div>
      <input id="SubmitButton" name="submit_release" type="submit" value="Release"/>
     </form>
   </div>
   <div id="Checklist">
   <h3>Pre Release Checklist</h3>
   <ul>
     <li>Dont forget to <b>increase the version number</b> in Version.txt.</li>
     <li>Run a <b>Dry</b> Release to make sure the generated files are correct. <a href="http://londeroth.org/~ck/dry-release">Dry Release Area</a></li>
     <li><b>Create a tag</b> for the release.</li>
   </ul>
   <h3>Post Release Checklist</h3>
   <ul>
     <li>Notify an openclonk.org admin to <b>upload the source package</b> that <a href="https://git.openclonk.org/openclonk.git/archive/">Isilkor will have generated</a> into the archive on openclonk.org. (The release scripts don't do this automatically yet.) His source packages still contain Tests.ocf, Experimental.ocf etc. They must be removed from the package uploaded on openclonk.org</li>
     <li><b>Notify Mortimer</b> about the release. He might want to supply us with a Mac binary. Only an openclonk.org admin can upload it. (The release scripts don't create Mac packages automatically yet.)</li>
     <li><b>Update our releases on <a href="http://www.desura.com/games/publish/openclonk/execute">desura.com</a></b> through the link at the bottom of the linked page. To generate the so called &quot;branch releases&quot; (Desura update packages), you need to install the Desura Desktop application and you need to run a Linux to create the Linux branch releases.<br/>Not registered? Drop a note in the internal board to be added to the group of OpenClonk Developers on Desura. </li>
     <li><b>Notify our Debian package maintainer</b> that a new version has been released.</li>
     <li><b>Make announcements</b> in our blog and optionally in our forum.</li>
     <li>Notify an openclonk.org admin to <b>mark this version as released in the bugtracker</b> and add the next version so the version info of future bugs can be set correctly.</li>
   </ul>
   </div>
   %(message)s
   <div id="Log">
     <h3>Recent log messages</h3>
     <div id="LogBody">
     </div>
   </div>
</html>""" % {
	'message': '<span class="%s">%s</span>' % (message_type, message_text) if len(message_text) > 0 else '',
	'target': os.path.basename(sys.argv[0]),
	'userlist': '\n'.join(['<option value="%(user)s">%(user)s</option>' % {'user': user} for user in users]),
}
