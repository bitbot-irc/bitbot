## Configure REST API

### Enable REST API
* `/msg <bot> config bot rest-api on`
* `/msg <bot> reloadmodule rest_api`

### Configure HTTPd
#### Nginx
* Copy example config file from [/docs/rest_api/nginx](/docs/rest_api/nginx) to `/etc/nginx/sites-enabled`
* Edit `server-name`, `ssl_certificate` and `ssl_certificate_key`
* `service nginx restart`
