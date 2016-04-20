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


@tornado.gen.coroutine
def migrate_names():
    # find mapping between user name and user login
    users = {}
    cursor = db.users.find()
    while (yield cursor.fetch_next):
        user = cursor.next_object()
        data = user.get('data')
        if data and data.get('name'):
            users[data['name']] = user['login']

    # replace name with login in all stored game rooms
    to_save = []
    cursor = db.rooms.find()
    while (yield cursor.fetch_next):
        game_room = cursor.next_object()
        if game_room.get('results'):
            for item in game_room['results']:
                if 'name' in item:
                    name = item.pop('name')
                    item['login'] = users.get(name, name)
                    to_save.append(game_room)

    for game_room in to_save:
        yield db.rooms.save(game_room)

    # replace name with login in hall of fame data, remove duplicates
    to_save = []
    to_remove = []
    cursor = db.results.find()
    while (yield cursor.fetch_next):
        result = cursor.next_object()
        if result['login'] in users:
            result['login'] = users[result['login']]
            to_save.append(result)
        elif '(' in result['login']:
            to_remove.append(result['_id'])

    for result in to_save:
        yield db.results.save(result)

    for _id in to_remove:
        yield db.results.remove({'_id': _id})


if __name__ == '__main__':
    tornado.ioloop.IOLoop.current().run_sync(ensure_indexes)
    tornado.ioloop.IOLoop.current().run_sync(setup_bot)
    tornado.ioloop.IOLoop.current().run_sync(migrate_names)
