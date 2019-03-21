# BitBot
Python3 event-driven modular IRC bot!

## Dependencies
[BeautifulSoup4](https://pypi.python.org/pypi/beautifulsoup4), [requests](https://pypi.org/project/requests/), [scrypt](https://pypi.python.org/pypi/scrypt), [suds](https://pypi.python.org/pypi/suds-jurko) and [twitter](https://pypi.python.org/pypi/twitter). Use `pip3 install -r requirements.txt` to install them all at once.

## Configurating
To get BitBot off the ground, there's some API-keys and the like in bot.conf.example. move it to bot.conf, fill in the API keys you want (and remove the ones you don't want - this will automatically disable the modules that rely on them.)

Run `./start.py` to run the bot with default settings (`--help` for more information) which will ask you for server details the first time you run it (run it again after filling out that information to get the bot going.) If you need to add more servers, use `./start.py --add-server`.

## Github web hooks
I run BitBot as-a-serivce on most popular networks and offer github-to-IRC web hook notifications for free to FOSS projects. Contact me for more information!

## Eagle
BitBot's National Rail module can optionally include output from Network Rail's SCHEDULE via [Eagle](https://github.com/EvelynSubarrow/Eagle). Configuration on BitBot's end is covered by the `eagle-` keys in bot.conf.example.

## Contact/Support
Come say hi at [#bitbot on freenode](https://webchat.freenode.net/?channels=#bitbot)
