#!/usr/bin/env python
import os
import re
import sys

import xmlrpclib
import hmac
import hashlib
import urllib

# config:
log_nlines = 50
user_blacklist = ['boom']

# startup:
basedir = os.path.dirname(os.path.realpath(sys.argv[0]))
users = sorted([user[4:-4] for user in os.listdir(os.path.join(basedir, 'keys')) if user.startswith('key-') and user.endswith('.txt') and user[4:-4] not in user_blacklist])
action = sys.stdin.read()

# logfile:
logfile = open(os.path.join(basedir, 'logs/oc-release.log'), 'r')
logfile.seek(0, 2)
size = logfile.tell()
logfile.seek(-min(log_nlines * 256, size), 1)
log = '<br />'.join([line for line in logfile.read().split('\n') if line.strip() != ''][-log_nlines:])

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
		message_text = 'Release scheduled. Please reload the page in a few seconds and check the log.'
		
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
   div#Form {
    margin-top: 5px;
    margin-right: 5px;
    padding: 5px;
    border: 1px black solid;
    float: left;
   }

   div#Log {
    margin-top: 5px;
    margin-left: 5px;
    border: 1px black solid;
    float: left;
   }

   div#LogHead {
    padding: 5px;
    border-bottom: 1px black solid;
    font-size: large;
    background-color: #FF8000;
   }

   div#LogBody {
    padding: 5px;
    background-color: #F3F781;
   }

   input#SubmitButton {
     background-color: #8A0808;
     color: #ffffff;
     font-size: large;
   }

   span.MessageSuccess {
     padding-left: 5px;
     padding-right: 5px;
     color: #FFFFFF;
     background-color: #088A08;
     font-weight: bold;
     border: 1px solid #084A08;
   }

   span.MessageError {
     padding-left: 5px;
     padding-right: 5px;
     color: #FFFFFF;
     background-color: #8A0808;
     font-weight: bold;
     border: 1px solid #4A0808;
   }
  </style>
 </head>

 <body>
  <img src="icon.png" style="float: left; margin-bottom: 20px; margin-right: 10px;"/> <h1>OpenClonk Release Interface</h1>

  <div style="clear: both;">
   %(message)s
   <div>
    <div id="Form">
     <form action="%(target)s" method="POST">
      <table>
       <tr>
        <td>User:</td>
        <td>
         <select name="user">
          %(userlist)s
         </select>
        </td>
       </tr>
       <tr>
        <td>Passphrase:</td>
        <td>
         <input name="passphrase" type="text" />
        </td>
       </tr>
       <tr>
        <td>Revision:</td>
        <td>
         <input name="revision" type="text" />
        </td>
       </tr>
       <tr>
        <td colspan="2" style="text-align: center;">
         <input type="submit" id="SubmitButton" value="Release!" name="submit_release" />
        </td>
       </tr>
      </table>
     </form>
    </div>

    <div id="Log">
     <div id="LogHead">
      Recent log messages
     </div>
     <div id="LogBody">
      <code>%(log)s</code>
     </div>
    </div>
   </div>
  </div>
 </body>
</html>""" % {
	'message': '<span class="%s">%s</span>' % (message_type, message_text) if len(message_text) > 0 else '',
	'target': os.path.basename(sys.argv[0]),
	'userlist': '\n'.join(['<option value="%(user)s">%(user)s</option>' % {'user': user} for user in users]),
	'log': log,
}
