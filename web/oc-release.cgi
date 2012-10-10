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

		if passphrase.strip() == '': raise Exception('Empty passphrase')
		if revision.strip() == '': raise Exception('Empty revision')

		proxy = xmlrpclib.ServerProxy('http://localhost:8000')
		ticket = proxy.oc_release_build_ticket(user)
		if type(ticket) != str: raise Exception('No such user')

		digest = hmac.new(passphrase.strip(), ticket, hashlib.sha256).hexdigest()
		result = proxy.oc_release_release(user, digest, revision)
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
     height: 370px;
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
   
   #SubmitButton {
     position: relative;
     top: 35px;
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
        <input id="Revision" name="revision" type="text" required="required"/>
      </div>
      <input id="SubmitButton" name="submit_release" type="submit" value="Release"/>
     </form>
   </div>
   <div id="Checklist">
   <h3>Release Checklist</h3>
   <ul>
     <li><b>Update our releases on <a href="http://www.desura.com/games/publish/openclonk/execute">desura.com</a></b> through the link at the bottom of the linked page. <br/>Not registered? At least Newton can add you to the group of OpenClonk Developers on Desura.</li>
     <li><b>Update our entry on <a href="http://www.ccan.de">ccan.de</a></b>. <br/>Forgot the password? Look it up in our internal board.</li>
     <li><b>Notify our Debian package maintainer</b> that a new version has been released.</li>
     <li><b>Make announcements</b> in our forum, in our blog and optionally in the <a href="http://www.clonk.de/forum/de">clonk.de</a> forum, in the clonk-center and other forums.</li>
   </ul>
   </div>
   %(message)s
   <div id="Log">
     <h3>Recent log messages</h3>
     <div id="LogBody"></div>
   </div>
</html>""" % {
	'message': '<span class="%s">%s</span>' % (message_type, message_text) if len(message_text) > 0 else '',
	'target': os.path.basename(sys.argv[0]),
	'userlist': '\n'.join(['<option value="%(user)s">%(user)s</option>' % {'user': user} for user in users]),
}
