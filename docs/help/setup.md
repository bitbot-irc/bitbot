## Setting up BitBot

* Move `bot.conf.example` to `bot.conf` and fill in the config options you care about. Ones blank or removed will disable relevant functionality.
* Run `./start.py -a` to add a server.
* Run `./start.py -m permissions -M master-password` to get the master admin password (needed to add regular admin accounts)
* Run `./start.py` to start the bot.
* Join `#bitbot` on a server with the bot (or invite it to another channel)
* `/msg <bot> register <password here>` to register your nickname with the bot
* `/msg <bot> masterlogin <master admin password>` to login as master admin
* `/msg <bot> givepermission <your nickname> *` to give your account admin permissions

### Configure client TLS certificate

Generate a TLS keypair and point `bot.conf`'s `tls-key` to the private key and `tls-certificate` to the public key.

### Configure SASL

Configure the bot to use SASL to authenticate (usually used for `NickServ` identification)

`EXTERNAL` usually mean client TLS certificate authentication; `USERPASS` is a BitBot-specific term that selects the strongest user/password algorithm.

> /msg <bot> config server sasl userpass &lt;username>:&lt;password>
> /msg <bot> config server sasl plain &lt;username>:&lt;password>
> /msg <bot> config server sasl scram-sha-1 &lt;username>:&lt;password>
> /msg <bot> config server sasl scram-sha-256 &lt;username>:&lt;password>
> /msg <bot> config server sasl external

### Commands on-connect

The `perform.py` module allows the bot to execute a saved list of raw IRC commands against a server it's connecting to. Use `/msg <bot> performadd <raw irc command>` to add to the current server's list of commands (`%nick%` in a raw command will be replaced with the bot's current nick.)

### Config options

#### View available config options

> /msg <bot> config bot|server|channel|user

#### Set config options

> /msg <bot> config bot <setting> <value>
> /msg <bot> config server <setting> <value>
> /msg <bot> config channel:#bitbot <setting> <value>
> /msg <bot> config user <setting> <value>
> /msg <bot> config user:other_user <setting> <value>
