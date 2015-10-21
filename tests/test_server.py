import datetime
import importlib
import json
import unittest
import unittest.mock

import tornado.testing
from tornado.concurrent import Future
from tornado.httpclient import AsyncHTTPClient

import server


ID = '000000000000000000000000'
TOKEN = '00000000-0000-0000-0000-000000000000'
LOGIN = 'stxnext'


def future_wrap(value):
    future = Future()
    future.set_result(value)
    return future


class GrotTestCase(tornado.testing.AsyncHTTPTestCase):

    def get_app(self):
        importlib.reload(server)

        return server.application


class UserTestCase(GrotTestCase):

    @unittest.mock.patch(
        'server.GameRoom.collection.save',
        return_value=future_wrap(ID)
    )
    @unittest.mock.patch(
        'server.User.collection.find_one',
        return_value=future_wrap({
            '_id': ID,
            'login': LOGIN,
            'token': TOKEN,
            'name': 'STXNext',
        })
    )
    @tornado.testing.gen_test(timeout=100000)
    def test_new_game_room(self, user_get, save_method):
        data = {
            'title': 'Test game_room',
        }
        client = AsyncHTTPClient(self.io_loop)
        response = yield client.fetch(
            self.get_url('/games?token={}'.format(TOKEN)),
            method='POST',
            body=json.dumps(data),
        )
        response = json.loads(response.body.decode())

        self.assertDictEqual({'room_id': ID}, response)

        args, kwargs = save_method.call_args
        save_data = kwargs['to_save']
        self.assertAlmostEqual(
            save_data.pop('timestamp'), datetime.datetime.now(),
            delta=datetime.timedelta(seconds=1)
        )
        expected = {
            'author': LOGIN,
            'auto_restart': 300,
            'auto_start': 300,
            'board_size': 5,
            'max_players': 15,
            'results': None,
            'title': data['title'],
            'with_bot': False
        }
        self.assertDictEqual(expected, save_data)

if __name__ == '__main__':
    unittest.main()
