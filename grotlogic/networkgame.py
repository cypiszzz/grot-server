import httplib
import json
import socket

from grotuserdbsdk.sdk import Contest, User

from .game import Game
from .utils import is_address_correct


class NetworkGame(object):

    def __init__(self, usergame):
        self.usergame = usergame

        contest = Contest.get(usergame.data['contest_id'])
        self.user = User.get(usergame.data['user_id'])
        self.game = Game(contest.data['size'], contest.data['seed'])

        self.correct_moves = 0
        self.wrong_moves = 0

    def next_move(self):
        if not self.is_active():
            return

        try:
            decision = self.get_decision()
            x, y = decision['x'], decision['y']

            self.handle_decision(x, y)

            self.usergame.save_round(decision, self.game.score)
        except (ValueError, socket.error):
            self.handle_wrong_decision()

    def get_decision(self):
        if not self.user.data['ip_address']:
            raise ValueError('Address not provided!')

        if not is_address_correct(self.user.data['ip_address']):
            raise ValueError('Incorrect address!')

        timeout = max(15 - self.wrong_moves * 3, 1)

        data = json.dumps(self.game.get_state())
        headers = {'Content-type': 'application/json'}

        connection = httplib.HTTPConnection(
            self.user.data['ip_address'],
            timeout=timeout
        )

        connection.request('POST', '/', data, headers)

        response = connection.getresponse()

        return json.loads(response.read().decode('utf-8'))

    def handle_decision(self, x, y):
        assert isinstance(x, int)
        assert isinstance(y, int)
        assert(0 <= x < self.game.board.size)
        assert(0 <= y < self.game.board.size)

        self.correct_moves += 1
        if self.correct_moves >= 5:
            self.wrong_moves = 0

        self.game.start_move(x, y)

    def handle_wrong_decision(self):
        self.wrong_moves += 1
        self.correct_moves = 0
        self.game.skip_move()

    def is_active(self):
        return self.game.is_active()

    def get_state(self):
        return {
            'score': self.game.score,
            'moves': self.game.moves,
            'name': self.user.data['user_name']
        }
