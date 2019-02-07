# Configuring SASL

You can either configure SASL through `!serverset sasl` from an registered and identified admin account or directly through sqlite.

## !serverset sasl

These commands are to be executed from a registered admin account

#### PLAIN
> !serverset sasl plain <username>:<password>

#### SCRAM-SHA-1
> !serverset sasl scram-sha-1 <username>:<password>

#### SCRAM-SHA-256
> !serverset sasl scram-sha-256 <username>:<password>

#### EXTERNAL
> !serverset sasl external

## sqlite

Execute these against the current bot database file (e.g. `$ sqlite3 databases/bot.db`)

#### PLAIN
> INSERT INTO server_settings (<serverid>, 'sasl', '{"mechanism": "plain", "args": "<username>:<password>"}');

#### SCRAM-SHA-1
> INSERT INTO server_settings (<serverid>, 'sasl', '{"mechanism": "scram-sha-1", "args": "<username>:<password>"}');

#### SCRAM-SHA-256
> INSERT INTO server_settings (<serverid>, 'sasl', '{"mechanism": "scram-sha-256", "args": "<username>:<password>"}');

#### external
> INSERT INTO server_settings (<serverid>, 'sasl', '{"mechanism": "external"}');
