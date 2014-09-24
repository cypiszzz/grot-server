import json
from unittest import TestCase

from mock import Mock, patch

from grotuserdbsdk.sdk import Contest, User

from ..networkgame import NetworkGame


class NetworkGameTestCase(TestCase):

    @patch.object(User, 'get')
    @patch.object(Contest, 'get')
    @patch('grotuserdbsdk.sdk.UserGame', spec=True)
    def setUp(self, usergame, contest_get, user_get):
        self.contest = Mock(data={
            'id': 1,
            'seed': 4,
            'size': 5
        }, spec=Contest)

        self.user = Mock(data={
            'id': 1,
            'username': 'Bob',
            'ip_address': '127.0.0.1:8000'
        }, spec=User)

        usergame.data = {
            'contest_id': 1,
            'user_id': 1
        }

        contest_get.return_value = self.contest
        user_get.return_value = self.user

        self.net_game = NetworkGame(usergame)

    @patch.object(NetworkGame, 'get_decision')
    def test_next_move(self, get_decision):
        get_decision.return_value = {'x': 0, 'y': 0}

        self.assertEqual(self.net_game.game.moves, 5)
        self.assertEqual(self.net_game.wrong_moves, 0)
        self.assertEqual(self.net_game.correct_moves, 0)

        self.net_game.next_move()
        self.assertEqual(self.net_game.game.moves, 4)
        self.assertEqual(self.net_game.wrong_moves, 0)
        self.assertEqual(self.net_game.correct_moves, 1)
        self.assertEqual(get_decision.call_count, 1)

        self.net_game.correct_moves = 3
        self.net_game.wrong_moves = 1
        self.net_game.next_move()
        self.assertEqual(self.net_game.game.moves, 3)
        self.assertEqual(self.net_game.wrong_moves, 1)
        self.assertEqual(self.net_game.correct_moves, 4)

        self.net_game.next_move()
        self.assertEqual(self.net_game.game.moves, 2)
        self.assertEqual(self.net_game.wrong_moves, 0)
        self.assertEqual(self.net_game.correct_moves, 5)

    @patch.object(NetworkGame, 'get_decision')
    def test_wrong_get_decision(self, get_decision):
        get_decision.side_effect = ValueError

        self.assertEqual(self.net_game.game.moves, 5)
        self.assertEqual(self.net_game.wrong_moves, 0)
        self.assertEqual(self.net_game.correct_moves, 0)

        self.net_game.next_move()
        self.assertEqual(self.net_game.game.moves, 4)
        self.assertEqual(self.net_game.wrong_moves, 1)
        self.assertEqual(self.net_game.correct_moves, 0)

        self.net_game.correct_moves = 1
        self.net_game.next_move()
        self.assertEqual(self.net_game.game.moves, 3)
        self.assertEqual(self.net_game.wrong_moves, 2)
        self.assertEqual(self.net_game.correct_moves, 0)

    @patch.object(NetworkGame, 'get_decision')
    @patch.object(NetworkGame, 'handle_decision')
    def test_wrong_handle_decision(self, handle_decision, get_decision):
        handle_decision.side_effect = ValueError

        self.assertEqual(self.net_game.game.moves, 5)
        self.assertEqual(self.net_game.wrong_moves, 0)
        self.assertEqual(self.net_game.correct_moves, 0)

        self.net_game.next_move()
        self.assertEqual(self.net_game.game.moves, 4)
        self.assertEqual(self.net_game.wrong_moves, 1)
        self.assertEqual(self.net_game.correct_moves, 0)

        self.net_game.correct_moves = 1
        self.net_game.next_move()
        self.assertEqual(self.net_game.game.moves, 3)
        self.assertEqual(self.net_game.wrong_moves, 2)
        self.assertEqual(self.net_game.correct_moves, 0)

    @patch('httplib.HTTPConnection')
    def test_get_decision(self, connection):
        decision = {'x': 3, 'y': 1}

        response = Mock()
        response.read.return_value = json.dumps(decision)

        connection_instance = Mock()
        connection_instance.getresponse.return_value = response

        connection.return_value = connection_instance

        self.assertEqual(self.net_game.get_decision(), decision)

    def test_handle_decision(self):
        self.net_game.handle_decision(0, 0)
        self.assertEqual(self.net_game.wrong_moves, 0)
        self.assertEqual(self.net_game.correct_moves, 1)
        self.assertEqual(self.net_game.game.moves, 4)

        with self.assertRaises(AssertionError):
            self.net_game.handle_decision(15, 15)

    def test_is_active(self):
        self.assertTrue(self.net_game.is_active())

        self.net_game.game.moves = 0

        self.assertFalse(self.net_game.is_active())
