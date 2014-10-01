import functools
import http.client
import json
import logging
import re

import tornado.escape
import tornado.gen
import tornado.ioloop
import tornado.web

from game import (
    Game,
    GameDev,
    GameDuel,
)
from grotlogic.board import Board
from user import (
    User,
    LocalUser,
)

# TODO seed
games = [
    GameDev(Board(5, 1)),
    Game(Board(5, 1)),
    GameDuel(Board(5, 1)),
]


def user(handler):
    @functools.wraps(handler)
    def wrapper(self, *args, **kwargs):
        if self.current_user is None:
            raise tornado.web.HTTPError(http.client.UNAUTHORIZED)

        return handler(self, *args, **kwargs)

    return wrapper


def admin(handler):
    @user
    def wrapper(self, *args, **kwargs):
        if not self.current_user.admin:
            raise tornado.web.HTTPError(http.client.FORBIDDEN)

        return handler(self, *args, **kwargs)

    return wrapper


def game(handler):
    @functools.wraps(handler)
    def wrapper(self, game, *args, **kwargs):
        try:
            #FIXME dirty workaround
            game_id = int(game)
            game = games[game_id]
            game.id = game_id
        except ValueError:
            raise tornado.web.HTTPError(http.client.BAD_REQUEST)
        except LookupError:
            raise tornado.web.HTTPError(http.client.NOT_FOUND)
        else:
            return handler(self, game, *args, **kwargs)

    return wrapper


class BaseHandler(tornado.web.RequestHandler):

    def get_current_user(self):
        token = self.get_query_argument('token', None)
        user = User.get(token)

        if not user and self.request.remote_ip == '127.0.0.1':
            return LocalUser(token or 'LocalUser')

        return user


class IndexHandler(BaseHandler):
    def get(self):
        self.redirect('/games')


class SignUpHandler(BaseHandler):
    def get(self):
        self.render('templates/signup.html')

    def post(self):
        name = tornado.escape.xhtml_escape(self.get_body_argument('name'))
        email = tornado.escape.xhtml_escape(self.get_body_argument('email'))

        if not name or not email:
            return self.render('templates/signup.html', **{
                'error': 'empty'
            })

        #TODO robust email validation?
        if not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            return self.render('templates/signup.html', **{
                'error': 'email'
            })

        if (
            User.collection.find_one({'name': name}) is not None
            or User.collection.find_one({'email': email}) is not None
        ):
            return self.render('templates/signup.html', **{
                'error': 'exists'
            })

        user = User(name, email)
        user.put()

        self.render('templates/thanks.html')


class GamesHandler(BaseHandler):

    def get(self):
        if 'html' in self.request.headers.get('Accept', 'html'):
            return self.render('templates/games.html', ** {
                'games': enumerate(games)
            })

        self.write({
            'games': range(len(games))
        })


class GameHandler(BaseHandler):

    @game
    def get(self, game):
        if 'html' in self.request.headers.get('Accept', 'html'):
            return self.render('templates/game.html', **{
                'game': game,
            })

    @admin
    @game
    def put(self, game):
        if not game.started:
            game.start()

    @admin
    @game
    def delete(self, game):
        if game.ended:
            games[game.id] = Game.new(board_size=5)


class GamePlayersHandler(BaseHandler):
    @tornado.gen.coroutine
    @game
    def get(self, game):
        if 'html' in self.request.headers.get('Accept', 'html'):
            self.render('templates/players.html', **{
                'game': game
            })

            raise tornado.gen.Return()

        while True:
            self.clear()
            self.write({
                'game': {
                    'started': game.started,
                    'ended': game.ended,
                },
                'players': [
                    {
                        'id': str(player.user.id),
                        'name': player.user.name,
                        'score': player.score,
                        'moves': player.moves,
                    }
                    for player in game.players
                ]
            })
            self.set_etag_header()

            if self.check_etag_header() and not game.ended:
                yield game.state_changed.wait()
            else:
                break


class GamePlayerHandler(BaseHandler):
    @tornado.gen.coroutine
    @game
    def get(self, game, user):
        try:
            player = game[user]
        except LookupError:
            raise tornado.web.HTTPError(http.client.NOT_FOUND)

        while True:
            self.clear()
            self.write(player.get_state(game.started))
            self.set_etag_header()

            if self.check_etag_header() and player.is_active():
                if game.started and not player.ready.is_set():
                    yield player.ready.wait()
                else:
                    yield game.next_round.wait()
            else:
                break


class GameBoardHandler(BaseHandler):

    @tornado.gen.coroutine
    @user
    @game
    def get(self, game):
        try:
            player = game[self.current_user]
        except LookupError:
            if game.started:
                raise tornado.web.HTTPError(http.client.FORBIDDEN)

            player = game.add_player(self.current_user)

        if not game.started:
            yield game.next_round.wait()

        self.write(player.get_state())

    @tornado.gen.coroutine
    @user
    @game
    def post(self, game):
        try:
            player = game[self.current_user]
        except LookupError:
            raise tornado.web.HTTPError(http.client.FORBIDDEN)

        if not game.started or game.ended or not player.is_active():
            raise tornado.web.HTTPError(http.client.METHOD_NOT_ALLOWED)

        try:
            data = json.loads(self.request.body.decode())

            x = int(data['x'])
            y = int(data['y'])
        except (
            KeyError,
            TypeError,
            ValueError,
        ):
            raise tornado.web.HTTPError(http.client.BAD_REQUEST)

        if not 0 <= x < player.board.size or not 0 <= y < player.board.size:
            raise tornado.web.HTTPError(http.client.BAD_REQUEST)

        if player.ready.is_set():
            yield game.next_round.wait()

        try:
            player.start_move(x, y)
        except Exception as e:
            logging.getLogger('tornado.application').exception(e)

        self.write(player.get_state())


application = tornado.web.Application([
    (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': 'static'}),
    (r'/', IndexHandler),
    (r'/signup', SignUpHandler),
    (r'/games', GamesHandler),
    (r'/games/(\d+)', GameHandler),
    (r'/games/(\d+)/board', GameBoardHandler),
    (r'/games/(\d+)/players/?', GamePlayersHandler),
    (r'/games/(\d+)/players/(\w+)', GamePlayerHandler),
], debug=True)

if __name__ == '__main__':
    application.listen(8080)
    tornado.ioloop.IOLoop.instance().start()
