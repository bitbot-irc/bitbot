#--depends-on commands
#--depends-on permissions

import json, re, time
from src import ModuleManager, utils

@utils.export("set",utils.BoolSetting("receive-messages","Whether or not you want to recieve messages."))
class Module(ModuleManager.BaseModule):
	_name="Tell"

	def _get_user_messages(self,user):
		return json.loads(user.get_setting("messages","[]"))
	def _set_user_messages(self,user,messages):
		user.set_setting("messages",json.dumps(messages))
	def _add_user_message(self,user,msg):
		messages = self._get_user_messages(user)
		messages.append(msg)
		self._set_user_messages(user,messages)
	def _reset_user_messages(self,user):
		self._set_user_messages(user,[])

	def _check_for_messages(self,event):
		target = event["user"]
		stdout = event["stdout"]
		messages = self._get_user_messages(target)
		if len(messages)==0: return
		elif len(messages)<5:
			for message in messages:
				stdout.write("%s: %s said: %s" % (target.nickname,message["sender_nickname"],message["text"]))
		else:
			for message in messages:
				target.send_message("%s said: %s" % (message["sender_nickname"],message["text"]))
			stdout.write("%s: %d messages for you" % (target.nickname,len(messages)))
		self._reset_user_messages(target)


	@utils.hook("command.regex")
	@utils.kwarg("expect_output",False)
	@utils.kwarg("ignore_action",False)
	@utils.kwarg("command","tell-trigger")
	@utils.kwarg("pattern",re.compile(".+"))
	def check_message(self, event):
		self._check_for_messages(event)

	@utils.hook("received.command.tell",min_args=2)
	@utils.kwarg("help","Leave a message")
	@utils.kwarg("usage","<user> <message>")
	def send_message(self,event):
		if not events["args_split"]: return
		user, message_parts = events["args_split"][0], events["args_split"][1:]
		user = event["server"].get_user(user)
		if not user.get_setting("receive-messages",True):
			event["stderr"].write("%s: The user you are trying to reach has disabled messages.")
			return
		message = " ".join(message_parts)
		self._add_user_message(user,dict(sender_nickname=event["user"].nickname,text=message,sent=time.time()))
		event["stdout"].write("%s: Message sent!")
