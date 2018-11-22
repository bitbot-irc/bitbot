Extra Information and Tips
======

## SSL Verification
To disable SSL verification (for example, if a server links to another)
Add to the server_settings table in bot.db:

| server_id | setting | value |
| --- | --- | --- |
| <server id> | ssl-verify  | false |

---

## SASL Authentication
Add to the server_settings table in bot.db:

| server_id | setting | value |
| --- | --- | --- |
| <server id> | sasl | {"mechanism": "PLAIN", "args": "username:password"} |

---

## User Identification (IRCv3)
If the server supports account-notify, you can use services to keep track of users, instead of having them register to your bot. To do that, insert the following into server_settings

| server_id | setting | value |
| --- | --- | --- |
| <server id> | identity-mechanism | "ircv3-account" |

* Note: Users will still be assigned a unique id, which is used for word tracking, permissions, etc. Internal user IDs do not correlate with registrations, so changing from ircv3-account to internal will not affect user tracking.
