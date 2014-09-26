import functools
import http.client
import json
import logging

import tornado.gen
import tornado.ioloop
import tornado.web

from game import Game

# TODO mutliple simultaneous games
games = [
    Game.new(board_size=5)
]


def user(handler):
    @functools.wraps(handler)
    def wrapper(self, *args, **kwargs):
        if self.current_user is None:
            raise tornado.web.HTTPError(http.client.UNAUTHORIZED)

        return handler(self, *args, **kwargs)

    return wrapper


# TODO admin login
def admin(handler):
    @user
    def wrapper(self, *args, **kwargs):
        if not self.current_user:
            raise tornado.web.HTTPError(http.client.FORBIDDEN)

        return handler(self, *args, **kwargs)

    return wrapper


def game(handler):
    @functools.wraps(handler)
    def wrapper(self, game, *args, **kwargs):
        try:
            game = games[int(game)]
        except ValueError:
            raise tornado.web.HTTPError(http.client.BAD_REQUEST)
        except LookupError:
            raise tornado.web.HTTPError(http.client.NOT_FOUND)
        else:
            return handler(self, game, *args, **kwargs)

    return wrapper


class BaseHandler(tornado.web.RequestHandler):

    # TODO user DB
    def get_current_user(self):
        try:
            return self.get_query_argument('user')
        except tornado.web.MissingArgumentError:
            return '0'


class IndexHandler(BaseHandler):
    def get(self):
        self.redirect('/games')


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
            games[0] = Game.new(board_size=5)


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
                        'id': player.user,
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
    def get(self, game, player):
        try:
            player = game[player]
        except LookupError:
            raise tornado.web.HTTPError(http.client.NOT_FOUND)

        self.write(player.get_state(game.started))
        self.set_etag_header()

        if self.check_etag_header() and player.is_active():
            if game.started and not player.ready.is_set():
                yield player.ready.wait()
            else:
                yield game.next_round.wait()

            self.clear()
            self.write(player.get_state())


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
    (r'/games', GamesHandler),
    (r'/games/(\d+)', GameHandler),
    (r'/games/(\d+)/board', GameBoardHandler),
    (r'/games/(\d+)/players', GamePlayersHandler),
    (r'/games/(\d+)/players/(\w+)', GamePlayerHandler),
], debug=True)

if __name__ == '__main__':
    application.listen(8080)
    tornado.ioloop.IOLoop.instance().start()
