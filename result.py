from datetime import datetime

import pymongo
import tornado.gen
from bson.son import SON

import settings


class Result(object):
    collection = settings.db['results']

    def __init__(self, **kwargs):
        self._id = kwargs.get('_id')
        self.login = kwargs.get('login', 'unknown')
        self.score = kwargs.get('score', 0)
        self.board_size = kwargs.get('board_size', 5)
        self.date = datetime.now()

    @property
    def result_id(self):
        return str(self._id) if self._id else None

    @classmethod
    @tornado.gen.coroutine
    def get_best(cls, board_size):
        cursor = yield Result.collection.aggregate(
            [
                {'$match': {'board_size': board_size}},
                {
                    '$group': {
                        '_id': '$login',
                        'score': {'$max': '$score'},
                    }
                },
                {"$sort": SON([("score", -1), ("_id", -1)])}
            ],
            cursor={}
        )
        results = yield cursor.to_list(length=100)
        return results

    def __lt__(self, other):
        return self.score > other.score

    @classmethod
    @tornado.gen.coroutine
    def get_last(cls, login, board_size):
        data = yield Result.collection.find_one(
            {'login': login, 'board_size': board_size},
            sort=[('score', pymongo.DESCENDING)]
        )
        return cls(**data) if data else None

    @tornado.gen.coroutine
    def put(self):
        data = {
            'login': self.login,
            'score': self.score,
            'date': self.date,
            'board_size': self.board_size,
        }
        result = yield Result.collection.save(data)
        return result
