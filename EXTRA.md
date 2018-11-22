Extra Information and Tips
======

## SSL Verification
To disable SSL verification (for example, if a server links to another)
Add to the server_settings table in bot.db:

| server_id | setting | value |
| --- | --- | --- |
| 1 | ssl-verify  | false |

---

## SASL Authentication
Add to the server_settings table in bot.db:

| server_id | setting | value |
| --- | --- | --- |
| 1 | sasl | {"mechanism": "PLAIN", "args": "username:password"} |

---

## User Identification (IRCv3)
If the server supports account-notify, you can use services to keep track of users, instead of having them register to your bot. To do that, insert the following into server_settings

| server_id | setting | value |
| --- | --- | --- |
| 1 | identity-mechanism | "ircv3-account" |

* Note: Users will still be assigned a unique id, which is used for word tracking, permissions, etc.
