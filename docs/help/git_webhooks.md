## Webhooks

### Give the bot an SSL-certificate

#### Self-signed certificate

***WARNING!*** Your git host may not accept self-signed certificates.

`openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 3650`

#### [acme.sh](https://github.com/Neilpang/acme.sh) certificate

Acme.sh is a [LetsEncrypt client](https://letsencrypt.org/). If you have
already [setup it](https://github.com/Neilpang/acme.sh/blob/master/README.md),
you can install a certificate for bitbot by: `/root/.acme.sh/acme.sh --install-cert -d <domain> --key-file /somewhere/bitbot/owns/key.pem --fullchain-file /somewhere/bitbot/owns/cert.pem`.

***WARNING!*** Always ensure that other users won't be able to read your
keys. `chmod -R 700 /path/to/directory/containing/<key.pem-and-cert.pem> &&  chown -R bitbotaccount:bitbotgroup /path/to/directory/containing/<key.pem-and-cert.pem>`

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

6. the bot will reply `[APIKey] New API key ('<name>'): <random-string>`.
   Keep the `<random-string>` at hand, you will need it in the next part.

7. add the repository to your channel with
   `!webhook add <username|organization>/<reponame>`. You can
   see the announced webhooks by `!webhook list` or remove them by
   `!webhook remove <name>`
    * you may `!webhook add `<username|orgname>` to accept all repositories
      from the user or organization.

### Configure the git host

This is generally done within settings of your repository and may depend
on the Git host. The details you need are:

* Target URL: `https://<your-bot-address>:<your-API-port>/api/<github|gitea>?key=<random-string>`
    * `<github|gitea>` means that you either enter `github` if you use
      GitHub or `gitea` if you use Gitea.
    * the `<random-string>` is the same the bot gave you in the previous
      step 6.
* HTTP Method: POST
* POST Content Type: `application/json` *or* `application/x-www-form-urlencoded`,
  bitbot supports both of them.

### Managing API keys

The API key isn't tied up to a specific git repository. It's recommended
that every user has their own API key.

This isn't implemented yet, see [issue #123](https://github.com/jesopo/bitbot/issues/123).

### Potential problems

* Response 401 means that your API key is wrong.
* Response 404 means that you haven't done `!webhook add <name>` anywhere
  yet.
