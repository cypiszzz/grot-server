import json
import tornado.gen
from tornado.httpclient import AsyncHTTPClient
import settings


GH_URLS = {
    'get_access_token': 'https://github.com/login/oauth/access_token',
    'get_user_data': 'https://api.github.com/user?access_token={}'
}


class OAuth(object):
    access_token = None
    gh_code = None

    def __init__(self, gh_code):
        self.client = AsyncHTTPClient()
        self.gh_code = gh_code

    @tornado.gen.coroutine
    def set_access_token(self):
        pay_load = {
            'client_id': settings.GH_OAUTH_CLIENT_ID,
            'client_secret': settings.GH_OAUTH_CLIENT_SECRET,
            'code': self.gh_code,
        }

        resp = yield self.client.fetch(
            GH_URLS['get_access_token'],
            method='POST',
            body=json.dumps(pay_load),
            headers={
                'content-type': 'application/json',
                'Accept': 'application/json',
            }
        )

        self.access_token = json.loads(resp.body.decode('utf8')).get('access_token', None)

    @tornado.gen.coroutine
    def get_user_data(self):
        if not self.access_token:
            yield self.get_access_token()

        resp = yield self.client.fetch(
            GH_URLS['get_user_data'].format(self.access_token),
            user_agent='GROT server'
        )
        return json.loads(resp.body.decode('utf8'))
