# BitBot
Python3 event-driven modular IRC bot!

## Dependencies
* [BeautifulSoup4](https://pypi.python.org/pypi/beautifulsoup4)
* [python-telegram-bot](https://pypi.org/project/python-telegram-bot/)
* [requests](https://pypi.org/project/requests/)
* [scrypt](https://pypi.python.org/pypi/scrypt)
* [suds](https://pypi.python.org/pypi/suds-jurko)
* [twitter](https://pypi.python.org/pypi/twitter)

Use `pip3 install -r requirements.txt` to install them all at once.

## Configurating
To get BitBot off the ground, there's some API-keys and the like in bot.conf.example. move it to bot.conf, fill in the API keys you want (and remove the ones you don't want - this will automatically disable the modules that rely on them.)

## Eagle
BitBot's National Rail module can optionally include output from Network Rail's SCHEDULE via [Eagle](https://github.com/EvelynSubarrow/Eagle). Configuration on BitBot's end is covered by the `eagle-` keys in bot.conf.example.

## Running
Just run `./start.py`

On first boot, he'll ask for a first server to connect to then exit. do `./start.py` again and he'll connect to that server and join #bitbot (to get him to join other channels, simply invite him to them.)

## Contact/Support
Come say hi at [##bitbot on freenode](https://webchat.freenode.net/?channels=##bitbot)
