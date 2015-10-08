import functools
import http.client
import json
import logging
import re
import requests
import uuid

import tornado.escape
import tornado.gen
import tornado.ioloop
import tornado.web

import settings
from game_room import GameRoom, DevGameRoom, RoomIsFullException
from user import User


log = logging.getLogger('grot-server')


DEV_GAME_ROOM = DevGameRoom(board_size=5)
game_rooms = GameRoom.get_all()


def user(handler):
    """
    Handler only for signed in users.
    """
    @functools.wraps(handler)
    def wrapper(self, *args, **kwargs):
        if self.current_user is None:
            raise tornado.web.HTTPError(http.client.UNAUTHORIZED)
        return handler(self, *args, **kwargs)

    return wrapper


def room_owner(handler):
    """
    Handler only for owner of a room.
    """
    @user
    def wrapper(self, game_room, *args, **kwargs):
        if game_room.author != self.current_user.login:
            raise tornado.web.HTTPError(http.client.FORBIDDEN)

        return handler(self, game_room, *args, **kwargs)

    return wrapper


def game_room(handler):
    """
    Get GameRoom object by room_id and pass it to the handler.
    """
    @functools.wraps(handler)
    def wrapper(self, room_id, *args, **kwargs):
        try:
            if room_id == '000000000000000000000000':
                game_room = DEV_GAME_ROOM
            else:
                game_room = game_rooms[room_id]
        except KeyError:
            raise tornado.web.HTTPError(http.client.NOT_FOUND)
        else:
            return handler(self, game_room, *args, **kwargs)

    return wrapper


class BaseHandler(tornado.web.RequestHandler):

    def get_current_user(self):
        """
        Search for token in GET, POST or cookie. Get User object by token.
        """
        token = self.get_query_argument('token', None)
        if not token:
            token = self.get_secure_cookie('token')
            if token:
                token = str(token, 'ascii')
        if not token and self.request.method == 'POST':
            try:
                data = json.loads(self.request.body.decode())
                token = data['token']
            except (ValueError, KeyError):
                pass
        return User.get(token)


class IndexHandler(BaseHandler):
    """
    Home page (help and sign in link).
    """

    def get(self):
        self.render(
            'templates/index.html',
            GH_OAUTH_CLIENT_ID=settings.GH_OAUTH_CLIENT_ID,
            current_user=self.current_user,
        )


class OAuthHandler(BaseHandler):
    """
    Finalize GitHub OAuth sign in, set cookie with token.
    """

    def get(self):
        gh_code = self.get_query_argument('code', None)
        if not gh_code:
            self.redirect('/')

        pay_load = {
            'client_id': settings.GH_OAUTH_CLIENT_ID,
            'client_secret': settings.GH_OAUTH_CLIENT_SECRET,
            'code': gh_code,
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
            self.redirect('/')

        resp = requests.get(
            'https://api.github.com/user?access_token=' + access_token
        )
        user_data = resp.json()

        login = user_data['login']
        user = User.get(login=login)
        if not user:
            user = User(login, data=user_data, gh_token=access_token)
            user.put()

        self.set_secure_cookie('token', user.token)
        self.redirect('/')


class GamesHandler(BaseHandler):

    def get(self):
        """
        List of game rooms.
        """
        if 'html' in self.request.headers.get('Accept', 'html'):
            return self.render(
                'templates/games.html',
                rooms=sorted(game_rooms.values())
            )

        self.write({
            'games': game_rooms.keys()
        })

    @user
    def post(self):
        """
        Create new game room.
        """
        data = json.loads(self.request.body.decode())
        if not data:
            raise tornado.web.HTTPError(http.client.BAD_REQUEST)

        def get_value(name, types, default=None, minimum=None, maximum=None):
            if name in data:
                val = data[name]
                if not isinstance(val, types):
                    raise tornado.web.HTTPError(
                        http.client.BAD_REQUEST,
                        'Wrong type of {}.'.format(name)
                    )
                if isinstance(val, (int, float)):
                    if minimum and val < minimum:
                        raise tornado.web.HTTPError(
                            http.client.BAD_REQUEST,
                            'Value of {} is too small.'.format(name)
                        )
                    if maximum and val > maximum:
                        raise tornado.web.HTTPError(
                            http.client.BAD_REQUEST,
                            'Value of {} is too big.'.format(name)
                        )
                if isinstance(val, str):
                    if minimum and len(val) < minimum:
                        raise tornado.web.HTTPError(
                            http.client.BAD_REQUEST,
                            '{} is too short.'.format(name)
                        )
                    if maximum and len(val) > maximum:
                        raise tornado.web.HTTPError(
                            http.client.BAD_REQUEST,
                            '{} is too long.'.format(name)
                        )
                return val
            return default

        none = type(None)
        board_size = get_value('board_size', int, 5, 3, 10)
        title = get_value('title', (str, none), None, 5, 100)
        max_players = get_value('max_players', int, 15, 2, 100)
        auto_start = get_value('auto_start', (int, none), 5, 1, 60)
        auto_restart = get_value('auto_restart', (int, none), 5, 1, 60)
        with_bot = get_value('with_bot', bool, False)
        author = self.current_user.login

        if auto_start:
            auto_start *= 60
        if auto_restart:
            auto_restart *= 60

        authors = [room.author for room in game_rooms.values()]
        if not self.current_user.admin and authors.count(author) >= 5:
            raise tornado.web.HTTPError(
                http.client.BAD_REQUEST,
                'Maximum number of rooms per user reached. '
                'Remove old rooms before creating new ones.'
            )

        titles = [room.title for room in game_rooms.values()]
        if not self.current_user.admin and title in titles:
            raise tornado.web.HTTPError(
                http.client.BAD_REQUEST,
                'Title already in use. Use unique title.'
            )

        game_room = GameRoom(board_size, title, max_players, auto_start,
                             auto_restart, with_bot, author)
        game_room.put()
        game_rooms[game_room.room_id] = game_room
        self.write({'room_id': game_room.room_id})


class GameHandler(BaseHandler):
    """
    Manage game rooms.
    """

    @tornado.gen.coroutine
    @game_room
    def get(self, game_room):
        """
        Game results page.
        """
        if 'html' in self.request.headers.get('Accept', 'html'):
            self.render('templates/game.html',
                game_room=game_room,
                user=self.current_user,
            )
            raise tornado.gen.Return()

        while True:
            self.write({
                'started': game_room.started,
                'ended': game_room.ended,
                'start_in': game_room.get_deadline('_auto_start'),
                'restart_in': game_room.get_deadline('_auto_restart'),
            })
            self.set_etag_header()

            if not self.check_etag_header():
                break

            self.clear()

            yield tornado.gen.sleep(1)

    @game_room
    @room_owner
    def post(self, game_room):
        """
        Start the game.
        """
        if not game_room.started:
            game_room.start()

    @game_room
    @room_owner
    def delete(self, game_room):
        """
        Remove game room.
        """
        room_id = game_room.room_id
        game_room.remove()
        del game_rooms[room_id]


class GameBoardHandler(BaseHandler):
    """
    Join game, make moves. Handler called from game client.
    """

    @tornado.gen.coroutine
    @user
    @game_room
    def get(self, game_room):
        """
        Join the game, wait for start. Returns first board state.
        """
        try:
            player = game_room[self.current_user]
        except LookupError:
            if game_room.started:
                raise tornado.web.HTTPError(http.client.FORBIDDEN)

            try:
                player = game_room.add_player(self.current_user)
            except RoomIsFullException:
                raise tornado.web.HTTPError(http.client.FORBIDDEN)

        if not game_room.started:
            yield game_room.on_progress.wait()

        self.write(player.get_state())

    @tornado.gen.coroutine
    @user
    @game_room
    def post(self, game_room):
        """
        Make a move on board. Returns board state after move.
        """
        try:
            player = game_room[self.current_user]
        except LookupError:
            raise tornado.web.HTTPError(http.client.FORBIDDEN)

        if not game_room.started or game_room.ended or not player.is_active():
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
            yield game_room.on_progress.wait()

        try:
            player.start_move(x, y)
        except Exception as e:
            logging.getLogger('tornado.application').exception(e)

        self.write(player.get_state())


class GamePlayersHandler(BaseHandler):
    """
    List of players in the game.
    """

    @tornado.gen.coroutine
    @game_room
    def get(self, game_room):
        """
        Stream list of players.
        """
        if 'html' in self.request.headers.get('Accept', 'html'):
            self.render('templates/players.html', game_room=game_room)
            raise tornado.gen.Return()

        while True:
            self.write({
                'players': game_room.get_results(),
            })
            self.set_etag_header()

            if not self.check_etag_header():
                break

            self.clear()

            if game_room.ended:
                self.set_status(http.client.NOT_MODIFIED)
                raise tornado.gen.Return()

            yield game_room.on_change.wait()


class GamePlayerHandler(BaseHandler):
    """
    Players board status.
    """

    @tornado.gen.coroutine
    @game_room
    def get(self, game_room, user):
        """
        Stream player board status.
        """
        try:
            player = game_room[user]
        except LookupError:
            raise tornado.web.HTTPError(http.client.NOT_FOUND)

        while True:
            self.write(player.get_state(game_room.started))
            self.set_etag_header()

            if not self.check_etag_header():
                break

            self.clear()

            if not player.is_active():
                self.set_status(http.client.NOT_MODIFIED)

                raise tornado.gen.Return()

            if game_room.started and not player.ready.is_set():
                yield player.ready.wait()
            else:
                yield game_room.on_progress.wait()


application = tornado.web.Application(
    [
        (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': 'static'}),
        (r'/', IndexHandler),
        (r'/gh-oauth', OAuthHandler),
        (r'/games', GamesHandler),
        (r'/games/([0-9a-f]{24})', GameHandler),
        (r'/games/([0-9a-f]{24})/board', GameBoardHandler),
        (r'/games/([0-9a-f]{24})/players/?', GamePlayersHandler),
        (r'/games/([0-9a-f]{24})/players/(\w+)', GamePlayerHandler),
    ],
    debug=True,
    cookie_secret=str(uuid.getnode()),
)

if __name__ == '__main__':
    log.warn('Starting server http://127.0.0.1:8080')
    application.listen(8080)
    tornado.ioloop.IOLoop.instance().start()
