# Configuring SASL

You can either configure SASL through `!serverset sasl` from an registered and identified admin account or directly through sqlite.

## USERPASS Mechanism

BitBot supports a special SASL mechanism name: `USERPASS`. This internally 
represents "pick the strongest username:password algorithm"

## !serverset sasl

These commands are to be executed from a registered admin account

#### USERPASS
> !serverset sasl userpass &lt;username>:&lt;password>

#### PLAIN
> !serverset sasl plain &lt;username>:&lt;password>

#### SCRAM-SHA-1
> !serverset sasl scram-sha-1 &lt;username>:&lt;password>

#### SCRAM-SHA-256
> !serverset sasl scram-sha-256 &lt;username>:&lt;password>

#### EXTERNAL
> !serverset sasl external

## sqlite

Execute these against the current bot database file (e.g. `$ sqlite3 databases/bot.db`)

#### USERPASS
> INSERT INTO server_settings (&lt;serverid>, 'sasl', '{"mechanism": "userpass", "args": "&lt;username>:&lt;password>"}');

#### PLAIN
> INSERT INTO server_settings (&lt;serverid>, 'sasl', '{"mechanism": "plain", "args": "&lt;username>:&lt;password>"}');

#### SCRAM-SHA-1
> INSERT INTO server_settings (&lt;serverid>, 'sasl', '{"mechanism": "scram-sha-1", "args": "&lt;username>:&lt;password>"}');

#### SCRAM-SHA-256
> INSERT INTO server_settings (&lt;serverid>, 'sasl', '{"mechanism": "scram-sha-256", "args": "&lt;username>:&lt;password>"}');

#### external
> INSERT INTO server_settings (&lt;serverid>, 'sasl', '{"mechanism": "external"}');
