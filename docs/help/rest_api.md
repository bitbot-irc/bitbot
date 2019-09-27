## Configure REST API

### Enable REST API
* `/msg <bot> config bot rest-api on`
* `/msg <bot> reloadmodule rest_api`

### Configure HTTPd
Either set up a reverse proxy (with persisted Host header) with your favourite HTTPd or follow the instructions below.

#### Nginx
* Copy example config file from [/docs/rest_api/nginx](/docs/rest_api/nginx) to `/etc/nginx/sites-enabled`
* Edit `server-name`, `ssl_certificate` and `ssl_certificate_key`
* `$ service nginx restart` as root

#### Apache2
* Run `$ a2enmod ssl proxy proxy_http` as root
* Copy example config file from [/docs/rest_api/apache2](/docs/rest_api/apache2) to `/etc/apache2/sites-enabled/`
* Edit `ServerName`, `SSLCertificateFile and `SSLCertificateKeyFile`
* `$ service apache2 restart` as root

#### Lighttpd
* Copy example config file from [/docs/rest_api/lighttpd](/docs/rest_api/lighttpd) to `/etc/lighttpd/lighttpd.conf`
* Edit `ssl.ca-file`, `ssl.pemfile` and `ssl.privkey`
* `$ service lighttpd restart` as root
