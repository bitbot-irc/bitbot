# TBD - BitBot v1.19.0 ("Command Specs Spark Joy")

Added:
- Commands Specs. expression language for defining format of command args
- `.bitbot/mod-data/` for addition data files for modules
- Concept of core vs additional modules. Core modules can be reloaded but not unloaded
- `channel_access` groups: `low`/`high`/`admin`
- Proof of concept reminders on a cron schedule (`cron_reminders.py`)
- Show how many seconds by which you missed a duck (`ducks.py`)
- Show gitlab wiki events (`git_webhooks`)
- Opt-in prune inactive channels after 2 weeks (`inactive_channels.py`)
- Ability to export decorated functions with @utils.export
- Configrable chance of randomly triggered markovs (`markov.py`)
- Ability to rewrite messages as well as block them (`message_filters.py`)
- Ability to search through recent messages (`messages.py`)
- `rainbow.py` because rainbow text is fun
- Track time/commit of load and events handled per module and show it through `!modinfo` (`modules.py`)
- Support ranges in stepped cron schedules (`cron.py`)
- Format `ACCOUNT` events (`format_activity.py`)
- Track channel list modes like ban, quiet, invex, ban exceptions (`mode_lists.py`)
- Support `WATCH` when available for `nick_regain.py`

Changed:
- IRCv3's `labeled-response` was ratified
- IRCv3's `setname` was ratified
- `channel_log` now logs to `.bitbot/mod-data/channel_log/`
- `channel_log` can now RSA+AES(CBC) encrypt log files
- Word tracking is now done per day. use `migration/v01.19.0-words.py` to migrate old data
- Totally rewrote `badges.py` command interface
- Huge refactor and rework of `channel_op.py` - most commands can take duration and globs now
- Improve `factoids.py` (including nested factoids)
- Split out `src/utils/datetime.py`
- Show github webhook issue/PR titles in more places (`git_webhooks`)
- Show google result descriptions instead of title when available (`google.py`)
- Minimal formatted lines should be relayed (`relay.py`)
- Totally rewrote `todo.py` command interface
- `IRCBuffer` now holds 1024 lines of history (was 64; 1024 might be overkill...)
- Reloaded modules will always be rolled back to previous loaded module if reload fails
- Generate usage from command spec stings when present (`help.py`)
- Much cleaner support for handling server `NOTICE`s (`line_handler`)
- `to_pretty_time` can now do relative time (e.g. including years and months)
- Souped HTTP responses changed from `lxml` parsing to `html5lib` by default
- Bool config options now accept 0 and 1

Fixed:
- Readded lost support for SASL `USERPASS` pseudo algo (`ircv3_sasl`)
- Minor typo in `healthchecks.py`
- Minor typo in `votes.py`
- Crash caused by division by zero in `title.py` difference checking
- `internal.identified` command was being fired for every message with an `@account` tag (`permissions`)

# 2020-01-20 - BitBot v1.18.2

Changed:
- Colourise server address in `server-notice` formatting (`format_activity.py`)

Fixed:
- `user` variable doesn't exist in `INVITE` formatting code (`format_activity.py`)
- `IRCBuffer.Buffer.find()`'s `not_pattern` arg should be optional
- `utils.datetime.iso8601_parse` no longer has a `microseconds` arg (`youtube.py`)

# 2020-01-20 - BitBot v1.18.1

Fixed:
- Formatting variable typo for handling TOPIC (`format_activity.py`)

# 2020-01-20 - BitBot v1.18.0

Added:
- New dependency in `requirements.txt`: `dateutils`
- Show `transferred` github issues by default (`git_webhooks`)
- `hostmask-tracking.py` - keep a history of what hostmasks each nickname has used
- Also watch `NICK` and `QUIT` lines to see when our nickname might be freee (`nick_regain.py`)
- IRCv3 `draft/delete` implementation (`ircv3_editmsg.py`)
- Show account and realname in `JOIN` formattin when available (`format_activity.py`)

Changed:
- Removed `--data-dir`, `--database` and `--log-dir`, these options have been moved to `bot.conf`
- Reworded karma change output
- `!grab` not tries to attach quote to account, not just nickname (`quotes.py`)
- `!wordiest` not defaults to the current channel (`words.py`)
- `!part` now works for `+o` users or users with channel_access `part` (`admin.py`)

Fixed:
- cron would fail to initialise at 59 minutes past the hour (`core_modules/cron.py`)
- Don't send typing notications by default for pattern-based commands
- Regex error when replacement starts with a number (`sed.py`)
- Reimplement lost IRCv3 `account-tag` functionality (`permissions`)
- Show username when fediverse displayname is "" (`fediverse`)
- `++asd++` used to give karma to both `asd++` and `++asd` (`karma.py`)

# 2020-01-08 - BitBot v1.17.2

Fixed:
- Incorrect format for HTTP UserAgent (missing ")")

# 2019-12-13 - BitBot v1.17.1

Fixed:
- Crash caused by switching `coins.py` to using `cron` scheduling without removing timer-related code
- Typo in function call name in `cron.py`

# 2019-12-13 - BitBot v1.17.0

Added:
- Ability to `.save()` `bot.conf` - we now use only this for module whitelist/blacklist
- A cron system (`src/core_modules/cron.py`)
- `healthcheck.py` - ping a URL every 10 minutes (for uptime-tracking services)
- Support `++nickname` style karma (`karma.py`)
- Bot-wide aliases (`!balias` in `aliases.py`)
- Support per-user (PM) `command-method` setting (`commands`)
- `dnsbl` module to loop up given IPv4 and IPv6 addresses in blacklists

Changed:
- "Core" modules (modules needed for base operation of bitbot) moved to `src/core_modules` and made blacklist-immune
- Better parsing error for `!config u birthday` (`birthday.py`)
- Show display name, not username, when available (`fediverse.py`)
- By default, show `locked`/`unlocked` github issue/PR events (`git_webhooks`)
- Switch back to full wolframalpha API but use it better than we used to (`wolframalpha.py`)
- Hostmasks are now precompiled to find users that match them (`permissions`)

Removed:
- `-m`/`-M` args to `bitbotd` - didn't work any more due to databse locking
- `database_backup.py` - this was always a weird hack. Added a note about backups in `README.md`

# 2019-12-01 - BitBot v1.16.1

Changed:
- Response to giving karma now makes sense

Fixed:
- Typo preventing users giving karma

# 2019-12-01 - BitBot v1.16.0

Added:
- Show target in formatted private `NOTICE` events (`format_activity.py`)
- Show first 100 chars of GitHub issue comments (`git_webhooks`)
- Show who opened a GitHub pull request when approperiate (`git_webhooks`)
- Timed user ignores (`ignore.py`)
- Support `"$$"` as `"$"` in command alias argument replacement (`aliases.py`)
- Show explicitly when only a title of an issue/PR was changed (`git_webhooks`)
- Show URLs in `!wikipedia` output (`wikipedia.py`)
- `!raw` and `!perform` now support "human" formats (e.g. `/msg user message`)
- Listing servers with `!servers` (`stats.py`)

Changed:
- Complete refactor of `permissions` module - now with hostmask support
- Big refactor of commands module
- Command aliases moved to their own module. Run `migration/v01.16.00-aliases.py` to migrate old aliases.
- Karma is now stored per-user and you can give yourself karma. Run `migration/v01.16.00-karma` to migrate old karma.
- Unique User-Agent (`utils.http.USERAGENT`)
- Nickname hashed colourisation now matches weechat's default (`utils.irc`)
- `./bitbotd -m permissions -M master-password` moved to `./bitbotctl command master-password`
- `utils.http.Response.data` is now always `bytes` - use `.decode()`/`.json()`/`.soup()`
- `to.py` -> `tell.py`; move `!to` to `!tell` but add `!to` as an alias
- Sed edits are now cumulative (`sed.py`)

# 2019-11-18 - BitBot v1.15.0

Added:
- Optionally colourise nicknames when printed to log (`format_activity.py` and `print_activity.py`)
- Show git branch in `!version` output (`info.py`)
- Stop/start REST API HTTPd when trying to reload all modules (`ModuleManager` and `rest_api.py`)
- Individual channels can opt out of printing to INFO log (`!config c print off`, `print_activity.py`)
- Opt-in shlex argument parsing for command callbacks (`commands`)
- Show when BitBot first saw you speak in `!words` output (`words.py`)

Changed:
- Logging moved to `~/.bitbot/logs/` by default
- Better eval API for `eval_python.py` (now py3 only)
- Better single-line normalisation for ActivityPub Activities (`fediverse`)
- Better error messages shown to user when a fediverse Actor can't be found (`fediverse`)
- Git hashes are now truncated to 7 chars, not 8 (`git_webhooks`)
- Split `utils/__init__.py` out in to more separate files
- Show channel mode status symbols when formatting `NOTICE`s (`format_activity.py`)
- Conbine YouTube API requests in to 1 request, rather than 3 (`youtube.py`)

Fixed:
- Multiple channel keys should be expressed as comma-separated (`channel_keys.py`)
- `!duckstats <nickname>` was meant to show stats for another user (`ducks.py`)
- Fix almost completely broken 908 (`RPL_SASLMECHS`) handling
- Background colour formatting was being lost (`utils.irc`)

Removed:
- `tfl.py` moved to `bitbot-modules`

# 2019-11-04 - BitBot v1.14.0

Added:
- Add Travis config to run `mypy`
- `!cmute`/`!cunmute` to mute/unmute a channel (`+m`) (`admin.py`)
- Support GitLab notes and confidential issues (`git_webhooks`)
- Strip `"'<>()` from words in titles when checking difference between a `<title>` and URL (`title.py`)
- Show when a youtube video was uploaded (`youtube.py`)
- 15 second SASL handshake timeout (`ircv3_sasl`)
- Ability to disable command suggestions (`command_suggestions.py`)
- Format/print/log `CHGHOST` events
- Show when a `!config` option has remained unchanged (`config.py`)
- Show GMT offset in `!time` output (`user_time.py`)

Changed:
- `/me` lines are no longer added to markov chains
- `!seen` last action (`seen-info`) is now per-channel, not per-network (`seen.py`)

Fixed:
- Rectified `src/utils/` circular dependency mess
- Decode fediverse data as utf8
- A bunch of typehinting errors across `src/`
- Switch to `lxml` for fediverse note parsing. `html.parser` was buggy and unpredictable (`fediverse`)

Removed:
- `!timezone`

# 2019-10-25 - BitBot v1.13.0

Added:
- `setup.py`
- `bitbotctl` - daemon control system through unix domain sockets
- Basic GitLab webhook support in `git_webhooks`
- Catch `m.youtube.com` URLs in `auto-youtube`
- Support UTF8 domains by punycode (idna) encoding
- `!` param in `!fedi` to denote "show content-warned content"
- Opt-in URL shortening for Gitea and GitLab
- `?channels=` GET param for git_webhooks to denote what channels should show activity
- `votes-cast-restricted` to restrict voting to voiced-or-above users

Changed:
- `start.py` -> `bitbotd`
- Database and config are now expected in `~/.bitbot/` (unless `--database` and `--config` are specified)
- Database backup files are now in `bot.db.{time}.back` format
- Don't say a users vote was changed when it wasn't (`vote.py`)
- Bot will not die when there's no connected servers
- Command output will be truncated/cut at "word bounaries" (currently only space)
- `!reloadallmodules` and `SIGUSR1` will not try to reload but rollback to currently-loaded on error
- `IRCBot.panic()` now just calls `sys.exit(20)` instead of trying to kill event loop

Fixed:
- Any user was able to add an API KEY (missing `permission` kwarg)
- Be able to `!disconnect` reconnection attempts (regression, `admin.py`)
- Strip only unknown tags from fedi `Note` activities - not the tag content too
- Don't allow users to `!bef`/`!trap` a triggered duck before it has quacked
- Don't set `location` to just a string when we decide a `!weather` arg is not a nickname
- We were not pulling out account ID from `WHOX` (just account name)
- Outdated `tornado` version in `requirements.txt`

Removed:
- `cve.py`
- `EVENTS.md`

# 2019-10-10 - BitBot v1.12.0

Added:
- Basic lock file mechanics (`src/LockFile.py`)
- `external_modules` - an arbitrary directory in which to look for modules
- `channel_blacklist.py` - rewrite `JOIN`s and send instant `PART`s to avoid the bot being in certain channels
- Ability to specify different `channel_op.py` `ban-mask` for users with accounts
- `!invite` in `channel_op.py`
- `check_certificate.py` - warn when a client certificate is close to expiration (or already expired)
- Support `$-` format for alias arg replacement - means "none or all args"
- Support `!config <nickname>`, `!config <#channel>` and `!config *`
- Support dice roll modifiers (e.g. `!roll 2d20+1-2`) in `dice.py`
- Opt-out highlight prevention for `!friends`/`!enemies` in `ducks.py`
- Use a random delay after a duck is triggered before showing the duck (`ducks.py`)
- `!friends`/`!enemies` now defaults to the current channel (`ducks.py`)
- `!action` and `!msg` in `echo.py`
- `git-show-private` channel setting to enable showing private github/gitea webhooks
- `!ghcommit` and support `auto-github` for `@commit`
- `!which` - show what module provides a command
- `!apropos` - show commands that contain a given string
- `!tcpup` - check if a given `host:port` can receive a TCP connection
- `markov.py`
- `mumble.py` - show stats for a given mumble server
- `!grab` as an alias of `!quotegrab`
- `!crate` in `rust.py` - show information on a given crate name
- Support sed `&` syntax
- Support `"<nickname>: s/"` sed syntax (search only for messages by `<nickname>`)
- `!silence` now takes an optional duration parameter
- `!unsilence`
- `!stats` not takes an optional network parameter - to show stats only for a given server
- `!channels` - list the bot's current channels on the current network
- `strip_otr.py` - remove trail whitespace used for automated OTR handshakes
- Support disabling `words.py` word tracking for a while channel
- `utils.deadline_process` - like `@utils.deadline` but uses a subprocess
- Single-line normalisation of fediverse Notes by vaguely parsing HTML
- Single-line normalisation of RSS titles
- Single-line normalisation of tweets

Changed:
- REST API only listens on localhost now, for security reasons
- `!changenickname` -> `!nick`
- `!reconnect` can take an `<alias>` param to tell it which server to reconnect to
- `!disconnect` can now cancel reconnections
- `auto_mode.py` was replaced by `!flags` in `channel_op.py`
- `!mute` masks should also take in to consideration the configured `ban-mask`
- Obscure output of `!config server sasl`
- `channel.get_user_status()` -> `channel.get_user_modes()`
- `!gh`/`!ghissue`/`!ghpull` can now see private repos through API keys
- Allow preventing user-specified nameservers with `!dns`
- Update `ircv3_multiline.py` to `draft/multiline`
- Prevent invalid SASL mechanisms
- `sasl-hard-fail` now defaults to False
- Multi-word karma now needs parentheses, along with a few other tweaks to prevent false positives
- `channel.topic_setter` is now a `Hostmask` object
- Obscure output of `!config server nickserv-password`
- `!quotegrab` can take a number of lines to grab
- `relay-extras` defaults to `False`
- `rest_api` responses now use a `Response` object for complex data and headers
- `!apikey` now has the subcommands `list`, `add`, `remove` and `info`
- `eval_rust.py` -> `rust.py`
- `!silence` now affects command usage errors and command suggestions
- Only do `auto-title` if the `<title>` and URL are significantly similar
- Use `"#<number>"` to denote `!ud` definition index
- Don't use an API for `user_time.py` - use `pytz`
- Support showing `!time` and `!weather` for a location, not just a user
- `Cache.py` is now more of a `key:value` store
- Temporarily cache IRCChannel settings in memory
- `utils.http.request()` now supports a complex request object
- `utils.http.request()` now uses more factors to detect a HTML page's encoding
- `utils.http.is_localhost()` -> `utils.http.host_permitted()` and reject more IP ranges
- `!editserver` should work for currently-disconnected servers
- `INFO` logging should go to a file - stdout should only be `WARN`

Fixed:
- `badges.py` now forces UTC
- `!op`/`!voice` in `channel_op.py` tried to use `send_mode()` without array arguments
- `!cignore` was not working for non-bot-admin users
- `!tw` should be asking for `tweet_mode="extended"`
- Fix `server.send_invite()` arg order
- `masterlogin` should only allow you to bypass `permission` checks, not e.g. `require_access` or `require_mode`

Removed:
- `books.py`
- `botsnack.py`
- `check_urls.py`
- `mixed_unicode.py`
- `!qget` - functionality moved to `!quote`
- `shakespeare.py`
- `slowvoice.py`
- `strax.py`
- `timer.py`

# 2019-08-30 - BitBot v1.11.1

Added:
- `utils.IntRangeSetting`
- `realname` was missing from `!editserver`

Changed:
- Added `"- "` to start of formatted kick lines
- Use `"+0000"` instead of `"Z"` for UTC timezone

Fixed:
- Put a deadline on sed matches to prevent DoS
- Duplicate `def op` in `channel_op.py` (due to copypaste)
- `git-prevent-highlight` was failing to unhighlight organisations

# 2019-08-15 - BitBot v1.11.0

Added:
- `rss.py`
- Show `weather.py` windspeed in MPh too
- `git_webhooks/gitea.py`
- `acronym.py`
- `!editserver` in `admin.py`
- `channel_keys.py` to centrally track/use channel keys
- `!mute` and `!unmute` in `channel_op.py`
- `command_suggestions.py`
- appendable command prefixes
- `@utils.kwarg`
- `fediverse.py`
- gitea webhooks (`git_webhooks/gitea.py`)
- Show available `!hash` algorithms
- per-channel-per-user ignores (`ignore.py`, `!cignore`)
- `ircv3.py` - to show ircv3 support stats
- `isup.py`
- `kick_rejoin.py`
- Handle `ERR_UNAVAILRESOURCE`
- `onionoo.py` (thanks @irl)
- `ops.py` to highlight ops (opt-in)
- Per-channel `perform.py` (`!cperform`)
- `proxy.py`
- Configurable URL shorteners (`shorturl.py`)
- `!unshorten` (`shorturl.py`)
- `slowvoice.py`
- `throttle.py`
- `!timezone` (`user_time.py`)
- Show `!weather` target nickname in command prefix
- Parse youtube playlists (`youtube.py`)
- `utils.http.url_sanitise()`
- `utils.http.request_many()`
- `./start.py --startup-disconnects`
- `./start.py --remove-server <alias>`
- `!remindme` as an alias of `!in` (`in.py`)
- `!source` and `!version` (`info.py`)
- Show TTL for DNS records (`ip_addresses.py`)
- `!addpoint`/`!rmpoint` as more explicit `++`/`--` for karma (`karma.py`)

Changed:
- Move `_check()` call to event loop func
- Split out github webhook functionality to `git_webhooks/github.py`
- Refactored @utils.export settings to be object-oriented
- Warn when channel-only/private-only is not met
- `8ball.py` -> `eightball.py` (can't import things that start with a digit)
- `github.py` -> `git_webhooks`
- revamp `!dns` to take optional nameserver and record typ
- `!quotedel` without quote removes most recent
- Relays moved to relay "groups" that channels can "join" and "leave"
- Rewrote `EventManager` for efficiency and simplicity
- Moved timers/cache/etc from read loop to event loop
- Better and more exhaustive channel move tracking
- Don't silently truncate `ParsedLine` at newline
- `@utils.hook`/`@utils.export` now use a single object that handles parsing
- `!ban`/`!kickban`/`!mute` duration syntax changed (`channel_op.py`)
- Highlight spam protection logic moved to own module (`highlight_spam.py`)
- `IRCBuffer.find()` returns the matched string
- Positive and negative karma throttled seperately (`karma.py`)
- REST API now listens in IPv6 (`rest_api.py`)

Fixed:
- Catch and rethrow not-found definitions in `define.py`
- `ircv3_botignore.py` event priority
- `CAP DEL` crash when `DEL`ing something that was not advertised
- `ParsedLine.format()` didn't prefix `source` with `":"`
- `_write_buffer` locking to avoid race condition
- `Capability().copy().depends_on` was mutable to the original copy

# 2019-06-23 - BitBot v1.10.0

Added:
- Outbound message filtering (`message_filter.py`)
- Mid-callback command permission checks ('event["check_assert"](utils.Check(...))')
- `connected-since` on stats endpoint
- IRCv3: draft/event-playback
- `auto-github-cooldown` to prevent duplicate `auto-github`s in quick succession
- `vote.py`
- IRCv3: `ircv3_botignore.py` to ignore users with `inspircd.org/bot`
- Catch and humanify `!loadmodule` "not found" exception
- cross-channel/network relay (`relay.py`)
- Option to allow anyone to `!startvote`
- IRCv3: CAP dependency system
- IRCv3: labeled-response + echo-message to correlate echos to sends
- `deferred_read.py`

Changed:
- Only strip 2 characters (`++` or `--`) from the end of karma
- Track CHANMODE type B, C and D (not just type D)
- 'x saved a duck' -> 'x befriended a duck'
- IRCv3: CAP REQ streamline for modules
- IRCv3: SASL failure defaults to being "hard" (disconnect/crash)
- `auto-title`, `auto-youtube`, `auto-imgur` etc now work in `/me`
- Move truncation logic from `SentLine` to `ParsedLine`
- Move `!help` logic to it's own file and rework it to be more user friendly
- Get `"city, state, country"` from geocoding in `location.py`, use in `weather.py`
- Convert IRC glob to regex, instead of using fnmatch
- `EventManager` calls can only come from the main thread
- IRCv3: `labeled-response` now depends on `batch`
- `format_activity.py` now only shows highest channel access symbol

Fixed:
- `KeyError` when sts `port` key not present
- lxml wasn't in requirements.txt but it should have been
- Any CRITICAL in read/write thread now kills the main thread too
- `Database.ChannelSettings.find` invalid SQL
- `birthday.py`'s year no longer .lstrip("0")ed
- IRCv3: pay attention to our own msgids (`ircv3_msgid.py`)
- catch and WARN when trying to remove a self-mode we didn't know we had
- `until_read_timeout` -> `until_read_timeout()`
- `PROTOCTL NAMESX` should have been send_raw() not send()
- IRCv3: handle `CAP ACK -<cap>`
- IRCv3: handle `CAP ACK` in response to `CAP REQ` that came from outside `ircv3.py`

Removed:
- `!set`/`!channelset`/`!serverset`/`!botset` (replaced with `!config`)
- `bytes-read-per-second` and `bytes-written-per-second` from stats endpoint
- `upc.py`

# 2019-06-09 - BitBot v1.9.2

Added:
- Show seconds it took to !bef/!trap

Changed:
- IRCv3: `draft/resume-0.4` -> `draft/resume-0.5`

Fixed:
- Fix scenario in which some-but-not-all threads die
- Daemonify tweet thread
- Don't add TAGMSGs to IRCBuffer objects

# 2019-06-08 - BitBot v1.9.1

Fixed:
- Fix ERROR on `CAP NEW` caused by STS typo
- Fix hanging on `CAP NEW` due to duplicate `REQ`
- STATUSMSG stripping should only be STATUSMSG symbols, not all PREFIX symbols

# 2019-06-07 - BitBot v1.9.0

Added:
- IRCv3: Also look at CTCP events for msgids
- Sub-event system within all SentLines
- Show last action in `!seen` (e.g. 'seen 1m ago (<jesopo> hi)')
- WARN when labels are not responded to in a timely fashion
- IRCv3: send `+draft/typing` while processing commands
- Display github `ready_for_review` better
- Parse 221 (RPL_UMODEIS) numerics

Changed:
- `!np` against a known nickname will attempt to resolve to lastfm username
- `PING` and `PONG` now avoid write throttling
- `!bang` -> `!trap`, 'shot' -> 'trapped' for ducks
- Socket reads and socket writes have been moved on to seperate threads
- Use Deques for chat history (more performant!)

Fixed:
- Differentiate between send and received CTCP events
- `IRCSocket._send` will now only return lines that definitely hit the wire
- GitHub `commit_comment` event formatting exception
- Strip xref tags from `!define` output
- `check_purge()` after removing contextual hooks from an EventHook
- IRCv3: Escape message tag values

# 2019-06-03 - BitBot v1.8.0

Added:
- Module dependency system
- Enable TCP keepalives
- IRCv3: `draft/label` tracking on every sent line when CAPs permit
- Enforce Python version 3.6.0 or later
- 'module-whitelist'/'module-blacklist' in `bot.conf`

Changed:
- IRCv3: Use last `server-time` for `RESUME` - not last .recv() time
- IRCv3: `draft/labeled-response` -> `draft/labeled-response-0.2`
- IRCv3: Prune already-seen messages in `chathistory` batches
- Consolidate `PRIVMSG`, `NOTICE` and `TAGMSG` handlers in to one

Fixed
- GitHub highlight prevention - don't detect highlights mid-word
- Pass already-decoded data in to BeautifulSoup
- !enablemodule actually removes module from blacklist setting
- Only enact write throttling when immediate-write-buffer is empty
- Non-throttled lines no longer delay throttled lines

# 2019-05-24 - BitBot v1.7.1

Fixed:
- Fix crash caused by CAP NEW

# 2019-05-23 - BitBot v1.7.0

Added:
- Add !addserver
- Add !masterpassword
- Add auto-tweet setting
- Support triggering commands by regex

Changed:
- Show usage examples for user/channel/server/bot settings
- Strip common command prefixes from PM commands so "!help" works
- Change auto-github to work for github urls too
- IRCv3: draft/resume-0.3 -> draft/resume-0.4
- Remove `ipv4` server attribute - figure it out automatically

Fixed:
- Typos/bugs in BATCH and FAIL
- Fix crash caused by BitBot messaging himself
