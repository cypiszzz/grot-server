import tornado.testing
import unittest
import unittest.mock
import importlib
import http.client

import game
import server


class GrotTestCase(tornado.testing.AsyncHTTPTestCase):

    def get_app(self):
        importlib.reload(server)

        return server.application


class UserTestCase(GrotTestCase):

    @unittest.mock.patch('server.User', autospec=True)
    def test_token(self, user):
        user.configure_mock(**{
            'get.return_value': user,
            'id': 1337,
            'name': 'STXNext',
            'token': '53CR3T',
        })

        def callback(response):
            response = response.body.decode()

            self.assertIn('id: \'{}\''.format(user.id), response)
            self.assertIn('name: \'{}\''.format(user.name), response)
            self.stop()

        self.http_client.fetch(
            self.get_url('/games/1/board?token={}'.format(user.token))
        )

        self.io_loop.call_later(
            1,
            lambda: self.http_client.fetch(
                self.get_url('/games/1'),
                callback,
            )
        )

        self.wait()

    @unittest.mock.patch('server.User', autospec=True)
    def test_local(self, user):
        user.configure_mock(**{
            'get.return_value': None,
            'name': 'LOCAL',
        })

        def callback(response):
            response = response.body.decode()

            self.assertIn('id: \'{}\''.format(user.name), response)
            self.assertIn('name: \'{}\''.format(user.name), response)
            self.stop()

        self.http_client.fetch(
            self.get_url('/games/1/board?token={}'.format(user.name))
        )

        self.io_loop.call_later(
            1,
            lambda: self.http_client.fetch(
                self.get_url('/games/1'),
                callback,
            )
        )

        self.wait()

    def test_admin(self):
        with unittest.mock.patch('server.User', autospec=True) as user:
            user.configure_mock(**{
                'get.return_value': user,
                'admin': False,
            })

            response = self.fetch('/games/1', method='DELETE')

            self.assertEqual(response.code, http.client.FORBIDDEN)

        with unittest.mock.patch('server.User', autospec=True) as user:
            user.configure_mock(**{
                'get.return_value': user,
                'admin': True,
            })

            response = self.fetch('/games/1', method='DELETE')

            self.assertEqual(response.code, http.client.OK)


class BoardTestCase(GrotTestCase):

    def setUp(self):
        super(BoardTestCase, self).setUp()

        self.user_patch = unittest.mock.patch('server.User', autospec=True)
        self.user = self.user_patch.start()
        self.user.configure_mock(**{
            'get.return_value': self.user,
            'id': 1337,
            'name': 'STXNext',
            'token': '53CR3T',
        })

    def test_join(self):
        def callback(response):
            response = response.body.decode()

            self.assertIn('id: \'{}\''.format(self.user.id), response)
            self.assertIn('name: \'{}\''.format(self.user.name), response)
            self.stop()

        self.http_client.fetch(
            self.get_url('/games/1/board?token={}'.format(self.user.token))
        )

        self.io_loop.call_later(
            1,
            lambda: self.http_client.fetch(
                self.get_url('/games/1'),
                callback,
            )
        )

        self.wait()

    def test_rejoin(self):
        def callback(response):
            response = response.body.decode()

            self.assertEqual(response.count('new Player('), 1)
            self.stop()

        self.test_join()

        self.http_client.fetch(
            self.get_url('/games/1/board?token={}'.format(self.user.token))
        )

        self.io_loop.call_later(
            1,
            lambda: self.http_client.fetch(
                self.get_url('/games/1'),
                callback,
            )
        )

        self.wait()
