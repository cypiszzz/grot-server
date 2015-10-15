GROT
====

Requirements
------------

* Python 3.5
* [tornadoweb](http://www.tornadoweb.org/)
* [mongodb](http://www.mongodb.org/)

Install
-------

	$ mkvirtualenv grot-server -p /usr/bin/python3.5
	$ pip3 install -r requirements.txt
	$ mkdir -p var/db
	$ mkdir -p var/log
	$ export BOT_TOKEN=`cat /proc/sys/kernel/random/uuid`
	$ echo "BOT_TOKEN = '$BOT_TOKEN'" >> settings.py
	$ mongo --eval "db.getSiblingDB('grot').users.insert({'token': '$BOT_TOKEN', 'login': 'stxnext', 'data': {'name': 'STX Next Bot', 'email': 'developer@stxnext.pl'}})"
	$ cd ..
	$ git clone git@github.com:stxnext/grot-stxnext-bot.git


Configure GitHub OAuth
----------------------

Fill in [Register a new OAuth application](https://github.com/settings/applications/new)
form. Save generated *Client ID* in `GH_OAUTH_CLIENT_ID` and  *Client Secret*
in `GH_OAUTH_CLIENT_SECRET` in `settings.py` file.

Run
---

### Server

	$ workon grot-server
	$ ./mongod
	$ python3 server.py

### Tests
    
    $ python3 tests/test_server.py
    $ python3 -m unittest discover


Client
------

For details check
[grot-client](https://github.com/stxnext/grot-client)
repository.