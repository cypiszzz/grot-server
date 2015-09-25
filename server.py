import functools
import http.client
import json
import logging
import re
import requests

import tornado.escape
import tornado.gen
import tornado.ioloop
import tornado.web

import settings
from game import (
    GameContest,
    GameDev,
    GameDuel,
)
from grotlogic.board import Board
from user import User

log = logging.getLogger('grot-server')

# TODO seed
games = [
    GameDev(Board(5)),
    GameDuel(Board(5)),
    GameContest(Board(5)),
]


#TODO dirty hack just before pycon
def restart_duel(future=None):
    def restart(future=None):
        games[1] = GameDuel(Board(5))

        restart_duel()

    def delay(future=None):
        tornado.ioloop.IOLoop.instance().call_later(
            10, restart
        )

    tornado.ioloop.IOLoop.instance().add_future(
        games[1].on_end.wait(), delay
    )

restart_duel()


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
        return User.get(token)


class IndexHandler(BaseHandler):
    def get(self):
        self.redirect('/games')


class SignInHandler(BaseHandler):
    def get(self):
        self.render('templates/signin.html', **{
            'GH_OAUTH_CLIENT_ID': settings.GH_OAUTH_CLIENT_ID
        })


class OAuthHandler(BaseHandler):
    def get(self):
        gh_code = self.get_query_argument('code', None)
        if not gh_code:
            self.redirect('/sign-in')

        pay_load = {
            'client_id': settings.GH_OAUTH_CLIENT_ID,
            'client_secret': settings.GH_OAUTH_CLIENT_SECRET,
            'code' : gh_code,
        }
        resp = requests.post(
            'https://github.com/login/oauth/access_token',
            data=json.dumps(pay_load),
            headers={
                'content-type': 'application/json',
                'Accept': 'application/json',
            }
        )
        access_token = resp.json().get('access_token', None)
        if not access_token:
            self.redirect('/sign-in')

        resp = requests.get(
            'https://api.github.com/user?access_token=' + access_token
        )
        user_data = resp.json()

        login = user_data['login']
        user = User.get(login=login)
        if not user:
            user = User(login, data=user_data, gh_token=access_token)
            user.put()

        self.render('templates/thanks.html', token=user.token, login=login)


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
                'user': self.current_user,
            })

    @admin
    @game
    def put(self, game):
        if not game.started:
            game.start()
        elif game.ended:
            games[2] = GameContest(Board(5))


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

            if not self.check_etag_header():
                break

            self.clear()

            if game.ended:
                self.set_status(http.client.NOT_MODIFIED)

                raise tornado.gen.Return()

            yield game.on_change.wait()


class GamePlayerHandler(BaseHandler):
    @tornado.gen.coroutine
    @game
    def get(self, game, user):
        try:
            player = game[user]
        except LookupError:
            raise tornado.web.HTTPError(http.client.NOT_FOUND)

        while True:
            self.write(player.get_state(game.started))
            self.set_etag_header()

            if not self.check_etag_header():
                break

            self.clear()

            if not player.is_active():
                self.set_status(http.client.NOT_MODIFIED)

                raise tornado.gen.Return()

            if game.started and not player.ready.is_set():
                yield player.ready.wait()
            else:
                yield game.on_progress.wait()


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

            try:
                player = game.add_player(self.current_user)
            except GameContest.PlayerNotQualifiedException:
                raise tornado.web.HTTPError(http.client.FORBIDDEN)

        if not game.started:
            yield game.on_progress.wait()

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
            yield game.on_progress.wait()

        try:
            player.start_move(x, y)
        except Exception as e:
            logging.getLogger('tornado.application').exception(e)

        self.write(player.get_state())


application = tornado.web.Application([
    (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': 'static'}),
    (r'/', IndexHandler),
    (r'/sign-in', SignInHandler),
    (r'/gh-oauth', OAuthHandler),
    (r'/games', GamesHandler),
    (r'/games/(\d+)', GameHandler),
    (r'/games/(\d+)/board', GameBoardHandler),
    (r'/games/(\d+)/players/?', GamePlayersHandler),
    (r'/games/(\d+)/players/(\w+)', GamePlayerHandler),
], debug=True)

if __name__ == '__main__':
    log.warn('Starting server http://127.0.0.1:8080')
    application.listen(8080)
    tornado.ioloop.IOLoop.instance().start()
