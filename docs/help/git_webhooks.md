## Webhooks

### Give the bot an SSL-certificate

#### Self-signed certificate

***WARNING!*** Your git host may not accept self-signed certificates.

`openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 3650`

#### [acme.sh](https://github.com/Neilpang/acme.sh) certificate

Assuming it's already installed and configured,

TODO: expand this

```
$ACMESH --key-file $BITBOTDIR/key.pem --fullchain-file $BITBOTDIR/cert.pem"
chmod -R 700 $BITBOTDIR/ssl.key
chown -R bitbot:bitbot $BITBOTDIR
```
### Configure the bot

1. Enable the REST API in bot.conf by adjusting

```
# key/cert used for REST API
tls-api-key              = /path/to/key.pem
tls-api-certificate      = /path/to/cert.pem
api-port                 = 5000
```

you may change the API port if you wish.

2. restart the bot or send it a `SIGUSR1` signal

3. enable the REST API by `!config bot rest-api on`

4. start the REST API for the first time by `!reloadmodule rest_api`

5. add your repository by `/msg <bot> apikey <reponame> /api/github`

6. the bot will reply `[APIKey] New API key ('<name>'): <random-string>`. Keep the `<random-string>` at hand, you will need it in the next part.

### Configure the git host

This is generally done within settings of your repository and may depend on the Git host. The details you need are:

* Target URL: `https://<your-bot-address>:<your-API-port>/api/github?key=<random-string>`
    * the `<random-string>` is the same the bot gave you in the previous step 6.
* HTTP Method: TODO: is it supposed to be POST or GET? I am assuming POST.
* POST Content Type: TODO: application/json or application/x-www-form-urlencoded ?
* Secret: the `<random-string>` which in case of Gitea was likely automatically moved here