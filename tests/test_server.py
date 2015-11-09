import datetime
import importlib
import json
import unittest
import unittest.mock

import tornado.testing
from tornado.concurrent import Future
from tornado.httpclient import AsyncHTTPClient
from xml.etree.ElementTree import fromstring
from random import randrange

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

    def setUp(self):
        super(GrotTestCase, self).setUp()
        self.client = AsyncHTTPClient(self.io_loop)

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
            'token': TOKEN
        }
        response = yield self.client.fetch(
            self.get_url('/games'),
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

        deleted = yield self.client.fetch(
            self.get_url('/games/{}?token={}'.format(ID, TOKEN)),
            method='DELETE',
        )
        self.assertEqual(deleted.code, 200)
        self.assertEqual(len(server.game_rooms), 0)

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
    @tornado.testing.gen_test()
    def test_new_game_exceptions(self, user_get):

        def new_room(body):
            return self.client.fetch(
                self.get_url('/games?token={}'.format(TOKEN)),
                method='POST',
                body=json.dumps(body),
            )

        bad_params = {
            'empty post data': {},
            'board_size too large': {'board_size': 15},
            'board_size too small': {'board_size': 1},
            'board_size type mismatch': {'board_size': '1'},
            'title too short': {'title': 't'},
            'title too long': {'title': 't'.join(
                [str(x) for x in range(0, 101)]
            )},
            'title duplicated': {'title': 'duplicated title'},
        }

        for msg, params in bad_params.items():
            with self.assertRaises(tornado.httpclient.HTTPError) as ex:
                yield new_room(params)

            self.assertEqual(ex.exception.code, 400, msg=msg)

        server.game_rooms['5'] = GameRoom(author=LOGIN)
        with self.assertRaises(tornado.httpclient.HTTPError) as ex:
            yield new_room({
                'title': 'rooms limit reached'
            })

        self.assertEqual(ex.exception.code, 400)

    @unittest.mock.patch(
        'tornado.locks.Event.is_set',
        return_value=False
    )
    @unittest.mock.patch(
        'server.game_rooms', {
            ID: GameRoom(
                _id=ID,
                author=LOGIN,
                allow_multi=True,
                max_players=2,
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
    @tornado.testing.gen_test()
    def test_join_and_play(self, get_user, player_ready):
        active_players = ['player1', 'player2']

        join1, join2 = yield [
            self.client.fetch(
                self.get_url('/games/{}/board?token={}&alias={}'.format(
                    ID, TOKEN, player
                )),
                method='GET'
            ) for player in active_players
        ]

        self.assertEqual(join1.code, 200)
        self.assertEqual(join2.code, 200)

        board = (yield self.client.fetch(
            self.get_url('/games/{}?token={}'.format(
                ID, TOKEN
            )),
            method='GET',
        )).body.decode()

        self.assertTrue("id: '{}{}'".format(ID, 'player1') in board)
        self.assertTrue("id: '{}{}'".format(ID, 'player2') in board)

        with self.assertRaises(tornado.httpclient.HTTPError) as ex:
            # try to join after start
            yield self.client.fetch(
                self.get_url('/games/{}/board?token={}'.format(ID, TOKEN)),
                method='GET',
            )
        self.assertEqual(ex.exception.code, 403)

        player_board = json.loads(join1.body.decode())
        expected_game = {
            'score': 0,
            'moves': 5,
            'moved': None,
        }

        for key, value in expected_game.items():
            self.assertTrue(key in player_board)
            self.assertEqual(player_board[key], value)

        scores = {}
        while len(active_players) > 0:
            for player in active_players:
                move = yield self.client.fetch(
                    self.get_url('/games/{}/board?alias={}&token={}'.format(
                        ID, player, TOKEN
                    )),
                    method='POST',
                    body=json.dumps({
                        'x': randrange(1, 5),
                        'y': randrange(1, 5),
                    }),
                )

                move = json.loads(move.body.decode())

                if move['moves'] == 0:
                    active_players.remove(player)
                    scores[player] = move['score']

        round_result = yield self.client.fetch(
            self.get_url('/games/{}'.format(ID)),
            method='GET',
            headers={'Accept': 'html'}
        )
        self.assertTrue(round_result.code, 200)

        round_result_page = round_result.body.decode()

        for player, score in scores.items():
            self.assertTrue("id: '{}{}'".format(
                ID, player
            ) in round_result_page)
            self.assertTrue("score: '{}'".format(score) in round_result_page)

        deleted = yield self.client.fetch(
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
    @tornado.testing.gen_test()
    def test_games_list(self):
        result = yield self.client.fetch(
            self.get_url('/games'),
            method='GET',
            headers={
                'Accept': 'html'
            }
        )

        body_str = result.body.decode()
        expected = '<a href="/games/{}">'.format(ID)
        self.assertTrue(expected in body_str)

    @tornado.testing.gen_test()
    def test_wrong_game(self):
        with self.assertRaises(tornado.httpclient.HTTPError):
            response = yield self.client.fetch(
                self.get_url('/games/{}'.format(ID)),
                method='GET'
            )
            self.assertEqual(response.code, 404)

    @tornado.testing.gen_test()
    def test_oauth_login(self):
        index_page = yield self.client.fetch(
            self.get_url('/gh-oauth'),
            method='GET',
        )

        index_html = index_page.body.decode().replace('&scope=user:email', '')
        root = fromstring(index_html)
        auth_url = root.find(".//a").attrib['href']

        expected = "https://github.com/login/oauth/authorize?client_id={}".format(
            settings.GH_OAUTH_CLIENT_ID
        )

        self.assertEqual(expected, auth_url)

    @unittest.mock.patch(
        'server.User.collection.save',
        return_value=future_wrap(ID)
    )
    @unittest.mock.patch(
        'server.User.collection.find_one',
        return_value=future_wrap(None)
    )
    @unittest.mock.patch(
        'server.OAuth.get_user_data',
        return_value=future_wrap({
            'login': 'Grzegorz Brzeczyszczykiewicz'
        })
    )
    @unittest.mock.patch(
        'server.OAuth.set_access_token',
        return_value=future_wrap(None)
    )
    @unittest.mock.patch(
        'server.OAuth.access_token',
        return_value='1234567890'
    )
    @tornado.testing.gen_test()
    def test_oauth_first_login(self, access_token, set_access_token, get_user_data, find_user, save_user):
        yield self.client.fetch(
            self.get_url('/gh-oauth?code=test'),
            method='GET',
        )

        args, kwargs = save_user.call_args

        self.assertEqual(args[0]['login'], 'Grzegorz Brzeczyszczykiewicz')
        self.assertRegex(args[0]['token'], r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
        self.assertEqual(args[0]['gh_token'], access_token)


if __name__ == '__main__':
    unittest.main()
