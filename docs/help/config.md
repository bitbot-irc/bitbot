## Setting up BitBot

* Move `docs/bot.conf.example` to `~/.bitbot/bot.conf` and fill in the config options you care about. Ones blank or removed will disable relevant functionality.
* Run `./bitbotd -a` to add a server.
* Run `./bitbotd` to start the bot or `./bitbotd -c /path/to/bot.conf` for non-standard config location (outside of `~/.bitbot`).
* Run `./bitbotctl command master-password` to get the master admin password (needed to add regular admin accounts)
* Join `#bitbot` on a server with the bot (or invite it to another channel)
* `/msg <bot> register <password here>` to register your nickname with the bot
* (use `/msg <bot> identify <password>` to log in in the future)
* `/msg <bot> masterlogin <master admin password>` to login as master admin
* `/msg <bot> permission add <your nickname> *` to give your account admin permissions

### Configure client TLS certificate

Generate a TLS keypair and point `bot.conf`'s `tls-key` to the private key and `tls-certificate` to the public key.

Below is an OpenSSL command example that will create a `bitbot-cert.pem` and `bitbot-key.pem` with `10y` validity (self-signed):
> openssl req -x509 -nodes -sha512 -newkey rsa:4096 -keyout bitbot-key.pem -out bitbot-cert.pem -days 3650 -subj "/CN=YourBotNick"

### Configure SASL

Configure the bot to use SASL to authenticate (usually used for `NickServ` identification)

`EXTERNAL` usually mean client TLS certificate authentication; `USERPASS` is a BitBot-specific term that selects the strongest user/password algorithm.

> /msg &lt;bot> config server sasl userpass &lt;username>:&lt;password>

> /msg &lt;bot> config server sasl plain &lt;username>:&lt;password>

> /msg &lt;bot> config server sasl scram-sha-1 &lt;username>:&lt;password>

> /msg &lt;bot> config server sasl scram-sha-256 &lt;username>:&lt;password>

> /msg &lt;bot> config server sasl external

### Commands on-connect

The `perform.py` module allows the bot to execute a saved list of raw IRC commands against a server it's connecting to. Use `/msg <bot> perform add <raw irc command>` to add to the current server's list of commands (`{NICK}` in a raw command will be replaced with the bot's current nick.)

### Config options

#### View available config options

> /msg &lt;bot> config bot|server|channel|user

#### Set config options

> /msg &lt;bot> config bot &lt;setting> &lt;value>

> /msg &lt;bot> config server &lt;setting> &lt;value>

> /msg &lt;bot> config channel:#bitbot &lt;setting> &lt;value>

> /msg &lt;bot> config user &lt;setting> &lt;value>

> /msg &lt;bot> config user:other_user &lt;setting> &lt;value>
