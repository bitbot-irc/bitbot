# Permissions

## Adding an admin user

This is a little complex at the moment but it will get easier some time soon.

### Registering user

Join a channel that BitBot is in (he'll automatically join #bitbot with default
configuration) and then type

> /msg &lt;botnick> register &lt;password>

### Give * permission

The `*` permission is a special permission that gives you completely unfettered 
access to all of BitBot's functions.

On IRC, send this to BitBot and take note of the ID response

> /msg &lt;botnick> myid

Then take that ID and open the database in sqlite3 (default database location is 
`databases/bot.db`

> $ sqlite3 databases/bot.db

And then insert your `*` permission

> INSERT INTO user_settings VALUES (&lt;id>, 'permissions', '["*"]');

(where `<id>` is the response from the `myid` command)

### Authenticating

To authenticate yourself as your admin user, use the following command

> /msg &lt;botnick> identify &lt;password>
