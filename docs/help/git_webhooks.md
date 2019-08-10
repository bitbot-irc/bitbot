## Webhooks

1. Generate a SSL certificate for the REST API. TODO: figure out the right
   way to do that.

Using acme.sh on the host already, I did TODO

```
$ACMESH --key-file $BITBOTDIR/ssl.key --cert-file $BITBOTDIR/ssl.cert --reloadcmd "$SYSTEMCTLRESTART bitbot"
chmod -R 700 $BITBOTDIR/ssl.key
chown -R bitbot:bitbot $BITBOTDIR
```

2. Enable the REST API in bot.conf by adjusting

```
# key/cert used for REST API
tls-api-key              = /path/to/just/generated/key
tls-api-certificate      = /path/to/just/generated/cert
api-port                 = 5000
```

you may change the API port if you wish.

3. restart the bot

4. run `!config bot rest-api on`.

5. Generate a random key for the git service to use, e.g. `pwgen 10`, pick
   one and remember it. `/msg <bot> apikey <name> /api/github`
