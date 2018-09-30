### Newly created objects
#### new.user
> user (IRCUser), server (IRCServer)
#### new.channel
> channel (IRCChannel), server (IRCServer)
#### new.server
> server (IRCServer)


### Default events
#### raw.[command]
> server (IRCServer), last (string), prefix (IRCPrefix), args (string[]), arbitrary (string), tags (dict)
#### received.numeric.[numeric]
> line (string), server (IRCServer), tags (dict), last (string), line_split (string[]), number (string)
#### received.[command]
> line (string), line_split (string[]), command (string), server (IRCServer), tags (dict), last (string)

### RPL_ISUPPORT
#### received.numeric.005
> isupport (string), server (IRCServer)

### Channel topics
#### received.numeric.332
> channel (IRCChannel), server (IRCServer), topic (string)
#### received.numeric.333
> channel (IRCChannel), setter (string), set_at (int), server (IRCServer)
#### received.topic
> channel (IRCChannel), server (IRCServer), topic (string), user (IRCUser)

### User activity in a channel
#### received.join
> channel (IRCChannel), user (IRCUser), server (IRCServer), account (string), realname (string)
#### received.part
> channel (IRCChannel), reason (string), user (IRCUser), server (IRCServer)
#### received.kick
> channel (IRCChannel), reason (string), target_user (IRCUser), user (IRCUser), server (IRCServer)
#### received.quit
> reason (string), user (IRCUser), server (IRCServer)
#### received.invite
> user (IRCUser), target_channel (string), server (IRCServer), target_user (IRCUser)
#### self.join
> channel (IRCChannel), server (IRCServer), account (string), realname (string)
#### self.part
> channel (IRCChannel), reason (string), server (IRCServer)
#### self.kick
> channel (IRCChannel), reason (string), user (IRCUser), server (IRCServer)

### NICK
#### self.nick
> server (IRCServer), new_nickname (string), old_nickname (string)
#### received.nick
> new_nickname (string), old_nickname (string), user (IRCUser), server (IRCServer)

### Channel/user modes
#### self.mode
> modes, server (IRCServer)
#### received.mode.channel
> modes, mode_args, channel (IRCChannel), server (IRCServer), user (IRCUser)

### IRCv3
#### received.cap.ls
> server (IRCServer), capabilities (dict)
#### received.cap.new 
> server (IRCServer), capabilities (dict)
#### received.cap.del
> server (IRCServer), capabilities (dict)
#### received.cap.ack
> server (IRCServer), capabilities (dict)
#### received.authenticate
> message (string), server (IRCServer)
#### received.tagmsg.channel
> channel (IRCChannel), user (IRCUser), tags (dict), server (IRCServer)
#### received.tagmsg.private
> user (IRCUser), tags (dict), server (IRCServer)
#### received.away.on
> user (IRCUser), server (IRCServer), message (string)
#### received.away.off
> user (IRCUser), server (IRCServer)
#### received.account.login
> user (IRCUser), server (IRCServer), account (string)
#### received.account.logout
> user (IRCUser), server (IRCServer)

### PRIVMSG (private/channel)
#### received.message.channel
> user (IRCUser), channel (IRCChannel), message (string), message_split (string[]), server (IRCServer), tags (dict), action (bool)
#### received.message.private
> user (IRCUser), message (string), message_split (string[]), server (IRCServer), tags (dict), action (bool)
#### self.message.channel
> message (string), message_split (string[]), channel (IRCChannel), action (bool), server (IRCServer)
#### self.message.private
> message (string), message_split (string[]), user (IRCUser), action (bool), server (IRCServer)

### NOTICE (private/channel/server)
#### received.server-notice
> message (string), message_split (string[]), server (IRCServer)
#### received.notice.channel
> message (string), message_split (string[]), user (IRCUser), server (IRCServer), channel (IRCChannel), tags (dict)
#### received.notice.private
> message (string), message_split (string[]), user (IRCUser), server (IRCServer), tags (dict)

### !commands
#### preprocess.command
> hook (EventCallback), user (IRCUser), server (IRCServer), target (IRCUser|IRCChannel), is_channel (bool), tags (dict)
#### received.command
> user (IRCUser), server (IRCServer), target (IRCUser|IRCChannel), args (string), args_split (string[]), stdout, stderr, command (string), is_channel (bool), tags (dict)
