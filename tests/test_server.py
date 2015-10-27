import datetime
import importlib
import json
from time import sleep
import unittest
import unittest.mock

import tornado.testing
from tornado.concurrent import Future
from tornado.httpclient import AsyncHTTPClient
import toro as toro
from game_room import GameRoom

import server
from user import User

ID = '000000000000000000000001'
ID_DEV = '000000000000000000000000'
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
        'server.GameRoom.collection.remove',
        return_value=None
    )
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
    def test_new_game_room(self, user_get, save_method, remove_method):
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

        self.assertEqual(len(server.game_rooms), 1)
        deleted = yield client.fetch(
            self.get_url('/games/{}?token={}'.format(ID, TOKEN)),
            method='DELETE',
        )
        self.assertEqual(deleted.code, 200)
        self.assertEqual(len(server.game_rooms), 0)

        args, kwargs = remove_method.call_args
        expected = ({'_id': ID},)
        self.assertEqual(expected, args)

    @unittest.mock.patch(
        'server.game_rooms', {
            ID: GameRoom(
                _id=ID,
                author=LOGIN
            )
        }
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
    @tornado.testing.gen_test(timeout=1000000)
    def test_join_and_play(self, get_user):
        client = AsyncHTTPClient(self.io_loop)

        join_result, start_result = yield [
            client.fetch(
                self.get_url('/games/{}/board?token={}&alias={}'.format(
                    ID, TOKEN, 'tester'
                )),
                method='GET'
            ),
            client.fetch(
                self.get_url('/games/{}?token={}'.format(ID, TOKEN)),
                method='POST',
                body=''
            )
        ]

        self.assertEqual(join_result.code, 200)
        self.assertEqual(start_result.code, 200)

        game = json.loads(join_result.body.decode())
        expected_game = {
            'score': 0,
            'moves': 5,
            'moved': None,
        }

        for key, value in expected_game.items():
            self.assertTrue(key in game)
            self.assertEqual(game[key], value)

        move_url = self.get_url('/games/{}/board?token={}'.format(ID, TOKEN))
        moves = [
            {'x': 3, 'y': 1},
            {'x': 1, 'y': 2},
        ]

        def make_move(self):
            if len(moves) == 0:
                return

            print('test')
            move = moves.pop()
            r = yield client.fetch(
                move_url,
                method='POST',
                body=json.dumps(move),
                callback=make_move
            )
            print(r)

        make_move(self)

        status = yield client.fetch(
            self.get_url('/games/{}/board?token={}&alias={}'.format(
                ID, TOKEN, 'tester'
            )),
            method='GET'
        )
        print(status)



    @unittest.mock.patch(
        'server.game_rooms', {
            ID: GameRoom(
                _id=ID,
                author=LOGIN
            )
        }
    )
    @tornado.testing.gen_test(timeout=100000)
    def test_game_result(self):
        client = AsyncHTTPClient(self.io_loop)
        result = yield client.fetch(
            self.get_url('/games'.format(ID)),
            method='GET',
            headers={
                'Accept': 'html'
            }
        )

        body_str = result.body.decode()
        expected = '<a href="/games/{}">'.format(ID)
        self.assertTrue(expected in body_str)


if __name__ == '__main__':
    unittest.main()
