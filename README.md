GROT
====

Requirements
------------

* python3
* [tornadoweb](http://www.tornadoweb.org/)
* [toro](http://toro.readthedocs.org/)
* [mongodb](http://www.mongodb.org/)
* [pymongo](http://api.mongodb.org/python/current/)

Install
-------

	$ mkvirtualenv grot-server -p /usr/bin/python3.4
	$ pip3 install -r requirements.txt
	$ mkdir -p var/db
	$ mkdir -p var/log
	$ mongo
	> use grot
	> db.users.insert({"token": "STXNext", "login": "STX Next Bot", "data": {"email": "developer@stxnext.pl"}})
	> exit
	$ cd ..
	$ git clone git@github.com:stxnext/grot-stxnext-bot.git

Run
---

### Server

	workon grot-server
	./mongod
	python3 server.py


Client
------

For details check
[grot-client](https://github.com/stxnext/grot-client)
repository.