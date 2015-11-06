import os
import sys

import pymongo
import tornado.gen
import tornado.ioloop

from settings import db, BOT_TOKEN


@tornado.gen.coroutine
def setup_bot():
    data = {
        'token': BOT_TOKEN,
        'login': 'stxnext',
        'data': {
            'name': 'STX Next Bot',
            'email': 'developer@stxnext.pl',
        }
    }

    bot_user = yield db.users.find_one({'login': 'stxnext'})
    if bot_user is not None:
        data['_id'] = bot_user['_id']

    yield db.users.save(data)


@tornado.gen.coroutine
def ensure_indexes():
    yield db.users.ensure_index([
        ('token', pymongo.HASHED),
    ])

    yield db.users.ensure_index([
        ('login', pymongo.HASHED),
    ])

    yield db.results.ensure_index([
        ('login', pymongo.HASHED),
    ])

    yield db.results.ensure_index([
        ('board_size', pymongo.HASHED),
    ])

    yield db.results.ensure_index([
        ('score', pymongo.HASHED),
    ])


if __name__ == '__main__':
    tornado.ioloop.IOLoop.current().run_sync(ensure_indexes)
    tornado.ioloop.IOLoop.current().run_sync(setup_bot)
