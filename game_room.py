import logging
import random
import subprocess
import time

from datetime import datetime

import tornado.gen
import tornado.locks
from tornado.ioloop import IOLoop

import settings
from result import Result
from grotlogic.board import Board
from grotlogic.game import Game


log = logging.getLogger('grot-server')


class RoomIsFullException(Exception):
    pass


class GameRoom(object):
    collection = settings.db['rooms']

    TIMEOUT = 10

    class Player(Game):

        def __init__(self, user, alias, allow_multi, board):
            super(GameRoom.Player, self).__init__(board)

            self.user = user
            self.alias = alias
            self.ready = tornado.locks.Event()
            self.moved = None
            self.inactive = False
            self.allow_multi = allow_multi

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

        def get_id(self):
            player_id = str(self.user.id)
            if self.allow_multi and self.alias:
                player_id += self.alias
            return player_id

        def get_login(self):
            player_login = str(self.user.login)
            if self.alias:
                player_login = '{} ({})'.format(player_login, self.alias)
            return player_login

    def __init__(self, board_size=5, title=None, max_players=15,
                 auto_start=5, auto_restart=5, with_bot=False,
                 allow_multi=False, author=None, timestamp=None,
                 results=None, _id=None):
        self._removed = False
        self._id = _id
        self.board_size = board_size
        self.title = title or 'Game {:%Y%m%d%H%M%S}'.format(datetime.now())
        self.max_players = max_players
        self.with_bot = with_bot
        self.allow_multi = allow_multi
        self.author = author
        self.timestamp = timestamp or datetime.now()
        self.results = results if not auto_start else None

        self._delays = {
            '_end_round': self.TIMEOUT,
            '_auto_start': auto_start,
            '_auto_restart': auto_restart,
        }

        self.seed = random.getrandbits(128)
        self.round = 0

        self.on_change = tornado.locks.Condition()
        self.on_end = tornado.locks.Condition()
        self.on_progress = tornado.locks.Condition()

        self._players = {}
        self._future = {}

        self.setup_timeout('_auto_start')

    @classmethod
    @tornado.gen.coroutine
    def get_all(cls):
        result = {}
        cursor = GameRoom.collection.find()
        while (yield cursor.fetch_next):
            game_room = cls(**cursor.next_object())
            result[game_room.room_id] = game_room
        return result

    @tornado.gen.coroutine
    def put(self):
        saved = self._id is not None
        data = {
            'title': self.title,
            'board_size': self.board_size,
            'max_players': self.max_players,
            'auto_start': self._delays['_auto_start'],
            'auto_restart': self._delays['_auto_restart'],
            'with_bot': self.with_bot,
            'allow_multi': self.allow_multi,
            'author': self.author,
            'timestamp': self.timestamp,
            'results': self.results,
        }

        if saved:
            data['_id'] = self._id

        if self._removed:
            log.warn('Updating already removed game room is not allowed!')
        else:
            self._id = yield GameRoom.collection.save(to_save=data)

    @tornado.gen.coroutine
    def remove(self):
        if self._id is not None:
            yield GameRoom.collection.remove({'_id': self._id})
        self._removed = True

    @property
    def room_id(self):
        return str(self._id) if self._id else None

    def __lt__(self, other):
        return self.timestamp > other.timestamp

    def get_player(self, user, alias=''):
        player_id = user if isinstance(user, str) else str(user.id)
        if self.allow_multi and alias:
            player_id += alias

        return self._players[player_id]

    def update_timestamp(self):
        self.timestamp = datetime.now()

    def setup_timeout(self, timeout_name):
        delay = self._delays.get(timeout_name)
        if delay:
            self.cancel_timeout(timeout_name)

            self._future[timeout_name] = IOLoop.instance().call_later(
                delay, getattr(self, timeout_name)
            )

    def cancel_timeout(self, timeout_name):
        handle = self._future.get(timeout_name)
        if handle:
            IOLoop.instance().remove_timeout(handle)
            del self._future[timeout_name]

    def get_deadline(self, timeout_name):
        handle = self._future.get(timeout_name)
        if handle:
            return int(handle.deadline - time.time())

    @property
    def started(self):
        return self.round != 0

    @property
    def ended(self):
        return bool(self.results)

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

    def add_player(self, user, alias=''):
        self.update_timestamp()
        if self.max_players and len(self._players) < self.max_players:
            player = self.Player(
                user, alias, self.allow_multi,
                Board(self.board_size, self.seed)
            )
            player_id = player.get_id()

            if player_id in self._players:
                # deactivate old player
                self._players[player_id].inactive = True

            self._players[player_id] = player

            self.on_change.notify_all()
        else:
            raise RoomIsFullException()

        player_logins = [p.user.login for p in self._players.values()]
        if self.with_bot and 'stxnext' not in player_logins:
            self.add_bot()

        if len(self._players) == self.max_players and \
           self._delays['_auto_start']:
            self.start()

        return player

    def _auto_start(self):
        if not self.started:
            if len(self._players) > 1:
                self.start()
            else:
                # not enought players - postpone start
                self.setup_timeout('_auto_start')

    def start(self):
        if not self.started:
            if len(self._players) <= 1:
                self.setup_timeout('_auto_start')
            else:
                self.cancel_timeout('_auto_start')
                self._new_round()
                self.on_change.notify_all()

    def _new_round(self):
        self.update_timestamp()
        self.round += 1

        for player in self.players_active:
            player.ready.clear()

            IOLoop.instance().add_future(
                player.ready.wait(), self._player_ready
            )

        self.setup_timeout('_end_round')

        self.on_progress.notify_all()

    def _end_round(self):
        self.update_timestamp()
        for player in self.players_unready:
            player.skip_move()

    def _player_ready(self, future):
        self.update_timestamp()
        self.on_change.notify_all()

        if any(self.players_unready):
            return

        self.cancel_timeout('_end_round')

        if any(self.players_active):
            self._new_round()
        else:
            # save results
            self.results = self.get_results()
            IOLoop.current().spawn_callback(self.put)
            IOLoop.current().spawn_callback(self.submit_result)
            self.setup_timeout('_auto_restart')
            self.on_end.notify_all()

    def get_results(self):
        if self.results:
            return self.results

        return [
            {
                'id': player.get_id(),
                'login': player.get_login(),
                'score': player.score,
                'moves': player.moves,
            }
            for player in self.players
        ]

    @tornado.gen.coroutine
    def submit_result(self):
        for result in self.get_results():
            if result['score'] > settings.MIN_HOF_SCORE:
                login = result['login']
                if ' ' in login:
                    login = login.split(' ')[0]
                lowest = yield Result.get_last(login, self.board_size)
                if lowest is None or lowest.score < result['score']:
                    result = Result(
                        login=login,
                        score=result['score'],
                        board_size=self.board_size,
                    )

                    yield result.put()

    def _auto_restart(self):
        self.cancel_timeout('_auto_restart')
        self._players = {}
        self.seed = random.getrandbits(128)
        self.round = 0
        self.results = None
        self.setup_timeout('_auto_start')

    def add_bot(self):
        subprocess.Popen(
            [
                'python3',
                '../grot-stxnext-bot/bot.py',
                settings.BOT_TOKEN,
                self.room_id,
            ]
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

    def get_player(self, user, alias=''):
        try:
            return super(DevGameRoom, self).get_player(user, alias)
        except LookupError:
            return self.add_player(user, alias)

    def start(self):
        pass

    def setup_timeout(self, timeout_name):
        pass

    def cancel_timeout(self, timeout_name):
        pass
