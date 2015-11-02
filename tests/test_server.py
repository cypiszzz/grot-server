import datetime
import importlib
import json
import unittest
import unittest.mock

import tornado.testing
from tornado.concurrent import Future
from tornado.httpclient import AsyncHTTPClient
from lxml.html import fromstring
from urllib.parse import urlparse, parse_qs

from game_room import GameRoom
import server
import settings

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
            1: GameRoom(author=LOGIN, title='duplicated title'),
            2: GameRoom(author=LOGIN),
            3: GameRoom(author=LOGIN),
            4: GameRoom(author=LOGIN)
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
    @tornado.testing.gen_test(timeout=100000)
    def test_new_game_exceptions(self, user_get):
        client = AsyncHTTPClient(self.io_loop)

        def new_room(body):
            return client.fetch(
                self.get_url('/games?token={}'.format(TOKEN)),
                method='POST',
                body=json.dumps(body),
            )

        bad_params = [
            {},  # empty post data
            {'title': 'too large', 'board_size': 15},
            {'title': 'too small', 'board_size': 1},
            {'title': 'wrong type', 'board_size': '1'},
            {'title': 't'},  # too short
            {'title': 't'.join([str(x) for x in range(0, 101)])},  # too long
            {'title': 'duplicated title'},
        ]

        for params in bad_params:
            with self.assertRaises(tornado.httpclient.HTTPError):
                response = yield new_room(params)
                self.assertEqual(response.code, 404)

        server.game_rooms['5'] = GameRoom(author=LOGIN)
        with self.assertRaises(tornado.httpclient.HTTPError):
            response = yield new_room({
                'title': 'rooms limit reached'
            })
            self.assertEqual(response.code, 404)

    @unittest.mock.patch(
        'server.game_rooms', {
            ID: GameRoom(
                _id=ID,
                author=LOGIN,
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
    @tornado.testing.gen_test(timeout=2000000)
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
                self.get_url('/games/{}'.format(ID)),
                method='POST',
                body=json.dumps({'token': TOKEN})
            )
        ]

        self.assertEqual(join_result.code, 200)
        self.assertEqual(start_result.code, 200)

        with self.assertRaises(tornado.httpclient.HTTPError):
            join_again = yield client.fetch(
                self.get_url('/games/{}/board?token={}'.format(ID, TOKEN)),
                method='GET',
            )
            self.assertEqual(join_again.code, 404)

        game = json.loads(join_result.body.decode())
        expected_game = {
            'score': 0,
            'moves': 5,
            'moved': None,
        }

        for key, value in expected_game.items():
            self.assertTrue(key in game)
            self.assertEqual(game[key], value)

        move = yield client.fetch(
            self.get_url('/games/{}/board'.format(ID)),
            method='POST',
            body=json.dumps({'x': 3, 'y': 1, 'token': TOKEN}),
        )
        move_result = json.loads(move.body.decode())
        self.assertTrue('score' in move_result)

        round_result = yield client.fetch(
            self.get_url('/games/{}'.format(ID)),
            method='GET',
            headers={
                'Accept': 'html'
            }
        )
        self.assertTrue(round_result.code, 200)

        round_result_page = round_result.body.decode()

        self.assertTrue("id: '{}'".format(ID) in round_result_page)
        self.assertTrue(
            "score: '{}'".format(move_result['score']) in round_result_page
        )

        deleted = yield client.fetch(
            self.get_url('/games/{}?token={}'.format(ID, TOKEN)),
            method='DELETE',
        )
        self.assertEqual(deleted.code, 200)
        self.assertEqual(len(server.game_rooms), 0)

    @unittest.mock.patch(
        'server.game_rooms', {
            ID: GameRoom(
                _id=ID,
                author=LOGIN
            )
        }
    )
    @tornado.testing.gen_test(timeout=100000)
    def test_games_list(self):
        client = AsyncHTTPClient(self.io_loop)
        result = yield client.fetch(
            self.get_url('/games'),
            method='GET',
            headers={
                'Accept': 'html'
            }
        )

        body_str = result.body.decode()
        expected = '<a href="/games/{}">'.format(ID)
        self.assertTrue(expected in body_str)

    @tornado.testing.gen_test(timeout=100000)
    def test_wrong_game(self):
        client = AsyncHTTPClient(self.io_loop)

        with self.assertRaises(tornado.httpclient.HTTPError):
            response = yield client.fetch(
                self.get_url('/games/{}'.format(ID)),
                method='GET'
            )
            self.assertEqual(response.code, 404)

    @tornado.testing.gen_test(timeout=100000)
    def test_oauth_login(self):
        client = AsyncHTTPClient(self.io_loop)
        index_page = yield client.fetch(
            self.get_url('/gh-oauth'),
            method='GET',
        )
        root = fromstring(index_page.body.decode())
        auth_url = root.xpath('//a')[0].attrib['href']

        qs = parse_qs(urlparse(auth_url).query)
        self.assertTrue('client_id' in qs)
        self.assertEqual(settings.GH_OAUTH_CLIENT_ID, qs['client_id'][0])

        login_form = yield client.fetch(auth_url, method='GET')

        expected_url = 'https://github.com/login?return_to='
        self.assertEqual(login_form.effective_url[:35], expected_url)

if __name__ == '__main__':
    unittest.main()
