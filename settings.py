import uuid

import motor


DEBUG = False

ADMINS = (
    'sargo',
    'AcidWeb',
    'tlewandowski',
    'lukaszjagodzinski',
)

MIN_HOF_SCORE = 100

COOKIE_SECRET = str(uuid.getnode())

GH_OAUTH_CLIENT_ID = ''
GH_OAUTH_CLIENT_SECRET = ''

BOT_TOKEN = ''


try:
    from local_settings import *
except ImportError:
    pass

db = motor.MotorClient().grot