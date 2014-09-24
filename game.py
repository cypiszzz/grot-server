import copy
import itertools

import tornado.concurrent
import tornado.ioloop

import grotlogic.board
import grotlogic.game


class Game(object):

    TIMEOUT = 10

    class Player(grotlogic.game.Game):

        def __init__(self, user, board):
            super(Game.Player, self).__init__(board)

            self.user = user
            self.ready = tornado.concurrent.Future()  # TODO toro.condition

        def start_move(self, x, y):
            try:
                super(Game.Player, self).start_move(x, y)
            finally:
                self.ready.set_result((x, y))

    def __init__(self, board):
        self.board = board
        self.round = 0

        self.next_round = tornado.concurrent.Future()  # TODO toro.condition

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

    def add_player(self, user):
        player = Game.Player(user, copy.copy(self.board))
        self._players[user] = player

        return player

    def start(self):
        self._new_round()

    def _new_round(self):
        self.round += 1

        for _, player in self._players.iteritems():
            tornado.ioloop.IOLoop.instance().add_future(
                player.ready, self._player_ready
            )

        self._future_round = tornado.ioloop.IOLoop.instance().call_later(
            self.TIMEOUT, self._end_round
        )

        self.next_round.set_result(self.round)
        self.next_round = tornado.concurrent.Future()

    def _end_round(self):
        for _, player in self._players.iteritems():
            if not player.ready.done():
                player.ready.set_result(None)

                if player.is_active():
                    player.skip_move()

            player.ready = tornado.concurrent.Future()

        active_players = itertools.imap(
            lambda item: item[1].is_active(),
            self._players.iteritems(),
        )

        if any(active_players):
            self._new_round()
        else:
            self._future_round = None

    def _player_ready(self, future):
        if not future.result():
            return

        for _, player in self._players.iteritems():
            if player.is_active() and not player.ready.done():
                return

        if self._future_round:
            tornado.ioloop.IOLoop.instance().remove_timeout(self._future_round)

        self._end_round()
