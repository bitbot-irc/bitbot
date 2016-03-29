# BitBot
Python3 event-driven modular IRC bot!

## Dependencies
* [BeautifulSoup4](https://pypi.python.org/pypi/beautifulsoup4/4.3.2)
* [twitter](https://pypi.python.org/pypi/twitter)

## Configurating
To get BitBot off the ground, there's some API-keys and the like in bot.json.example. move it to bot.json, fill in the API keys you want (and remove the modules that rely on those configs.)

## Running
Just run `./start.py`

On first boot, it'll ask for a first server to connect to then exit. do `./start.py` again and it'll connect to that server and join #bitbot.

## Data storage
The main data storage for Bitbot is done in his sqlite3 database, bot.db.
