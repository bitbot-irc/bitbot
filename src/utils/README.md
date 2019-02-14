Extra Information and Tips
======

## SSL Verification
To disable SSL verification (for example, if a server links to another)
Run the following SQL command

> INSERT INTO server_settings (&lt;serverid>, 'ssl-verify', 'false');