import random
import subprocess

from datetime import datetime

import tornado.ioloop
import toro

import settings
from grotlogic.board import Board
from grotlogic.game import Game

class RoomIsFullException(Exception):
    pass


class GameRoom(object):
    collection = settings.db['rooms']

    TIMEOUT = 10

    class Player(Game):

        def __init__(self, user, board):
            super(GameRoom.Player, self).__init__(board)

            self.user = user
            self.ready = toro.Event()
            self.moved = None

        def start_move(self, x, y):
            try:
                super(GameRoom.Player, self).start_move(x, y)
            finally:
                self.moved = (x, y)
                self.ready.set()

        def skip_move(self):
            try:
                super(GameRoom.Player, self).skip_move()
            finally:
                self.moved = None
                self.ready.set()

        def get_state(self, board=True):
            state = super(GameRoom.Player, self).get_state(board)
            state.update({
                'moved': self.moved
            })

            return state

    def __init__(self, board_size=5, title=None, max_players=15,
                 auto_start=5, auto_restart=5, with_bot=False, author=None,
                 timestamp=None, _id=None, results=None):
        self._id = _id
        self.board_size = board_size
        self.title = title or 'Game room {:%Y%m%d%H%M%S}'.format(datetime.now())
        self.max_players = max_players
        self.auto_start = auto_start
        self.auto_restart = auto_restart
        self.with_bot = with_bot
        self.author = author
        self.timestamp = timestamp or datetime.now()
        self.results = results

        self.seed = random.getrandbits(128)
        self.round = 0

        self.on_change = toro.Condition()
        self.on_end = toro.Condition()
        self.on_progress = toro.Condition()

        self._players = {}
        self._future_round = None

        # TODO - if auto_start then setup start game trigger
        # TODo - if with_bot then start bot

    @classmethod
    def get_all(cls):
        return {
            str(data['_id']): cls(**data)
            for data in GameRoom.collection.find()
            if data
        }

    def put(self):
        saved = self._id is not None
        data = {
            'title': self.title,
            'board_size': self.board_size,
            'max_players': self.max_players,
            'auto_start': self.auto_start,
            'auto_restart': self.auto_restart,
            'with_bot': self.with_bot,
            'author': self.author,
            'timestamp': self.timestamp,
            'results': self.results,
        }

        if saved:
            data['_id'] = self._id

        self._id = GameRoom.collection.save(data)

    def remove(self):
        if self._id is not None:
            GameRoom.collection.remove({'_id': self._id})

    @property
    def room_id(self):
        return str(self._id) if self._id else None

    def __lt__(self, other):
        return self.timestamp < other.timestamp

    def __getitem__(self, user):
        user = user if isinstance(user, str) else str(user.id)

        return self._players[user]

    @property
    def started(self):
        return self.round != 0

    @property
    def ended(self):
        return self.started and self._future_round is None

    @property
    def players(self):
        players = list(self._players.values())
        players.sort(
            key=lambda player: (player.score, player.moves),
            reverse=True,
        )
        return players

    @property
    def players_active(self):
        return (
            player
            for player in self._players.values()
            if player.is_active()
        )

    @property
    def players_unready(self):
        return (
            player
            for player in self.players_active
            if not player.ready.is_set()
        )

    def add_player(self, user):
        if self.max_players and len(self._players) < self.max_players:
            player = self.Player(user, Board(self.board_size, self.seed))
            self._players[str(user.id)] = player

            self.on_change.notify_all()
        else:
            raise RoomIsFullException()

        if len(self._players) == self.max_players and self.auto_start:
            self.start()

        return player

    def start(self):
        if not self.started:
            self._new_round()

    def _new_round(self):
        self.round += 1

        for player in self.players_active:
            player.ready.clear()

            tornado.ioloop.IOLoop.instance().add_future(
                player.ready.wait(), self._player_ready
            )

        self._future_round = tornado.ioloop.IOLoop.instance().call_later(
            self.TIMEOUT, self._end_round
        )

        self.on_progress.notify_all()

    def _end_round(self):
        for player in self.players_unready:
            player.skip_move()

    def _player_ready(self, future):
        self.on_change.notify_all()

        if any(self.players_unready):
            return

        if self._future_round:
            tornado.ioloop.IOLoop.instance().remove_timeout(self._future_round)

            self._future_round = None

        if any(self.players_active):
            self._new_round()
        else:
            # save results
            self.results = self.get_results()
            self.put()
            self.on_end.notify_all()

    def get_results(self):
        if self.results:
            return self.results

        return [
            {
                'id': str(player.user.id),
                'name': player.user.name,
                'score': player.score,
                'moves': player.moves,
            }
            for player in self.players
        ]

    def add_bot(self, user):
        subprocess.Popen(
            ['python3', '../grot-stxnext-bot/bot.py', self.room_id]
        )


class DevGameRoom(GameRoom):

    class Player(GameRoom.Player):
        def start_move(self, x, y):
            try:
                self.moves = 1
                self.score = 0

                super(DevGameRoom.Player, self).start_move(x, y)
            finally:
                self.ready.clear()

        def skip_move(self):
            pass

        def is_active(self):
            return True

    @property
    def started(self):
        return True

    @property
    def ended(self):
        return False

    @property
    def players(self):
        return []

    def __getitem__(self, user):
        try:
            return super(DevGameRoom, self).__getitem__(user)
        except LookupError:
            return self.add_player(user)

    def start(self):
        pass
