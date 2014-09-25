import copy

import tornado.ioloop
import toro

import grotlogic.board
import grotlogic.game


class Game(object):

    TIMEOUT = 10

    class Player(grotlogic.game.Game):

        def __init__(self, user, board):
            super(Game.Player, self).__init__(board)

            self.user = user
            self.ready = toro.Event()

        def start_move(self, x, y):
            try:
                super(Game.Player, self).start_move(x, y)
            finally:
                self.ready.set()

    def __init__(self, board):
        self.board = board
        self.round = 0

        self.next_round = toro.Condition()

        self._players = {}
        self._future_round = None

    def __getitem__(self, user):
        return self._players[user]

    @classmethod
    def new(cls, board_size=5):
        return cls(grotlogic.board.Board(board_size, 1))  # TODO testing seed

    @property
    def started(self):
        return self.round != 0

    @property
    def ended(self):
        return self.started and self._future_round is None

    @property
    def players(self):
        players = self._players.values()
        players = sorted(
            players,
            key=lambda player: player.user
        )
        players = sorted(
            players,
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
        player = Game.Player(user, copy.copy(self.board))
        self._players[user] = player

        return player

    def start(self):
        self._new_round()

    def _new_round(self):
        self.round += 1

        for player in self._players.values():
            tornado.ioloop.IOLoop.instance().add_future(
                player.ready.wait(), self._player_ready
            )

        self._future_round = tornado.ioloop.IOLoop.instance().call_later(
            self.TIMEOUT, self._end_round
        )

        self.next_round.notify_all()

    def _end_round(self):
        for player in self._players.values():
            if not player.ready.is_set():
                if player.is_active():
                    player.skip_move()

                player.ready.set_exception(toro.Timeout)

            player.ready.clear()

        if any(self.players_active):
            self._new_round()
        else:
            self._future_round = None

    def _player_ready(self, future):
        if future.exception():
            return

        if any(self.players_unready):
            return

        if self._future_round:
            tornado.ioloop.IOLoop.instance().remove_timeout(self._future_round)

        self._end_round()
