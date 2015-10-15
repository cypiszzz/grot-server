import motor
import pymongo
import uuid

DEBUG = False

db = motor.MotorClient().grot

db['users'].ensure_index([
    ('token', pymongo.HASHED),
])
db['users'].ensure_index([
    ('login', pymongo.HASHED),
])


ADMINS = (
    'sargo',
)

COOKIE_SECRET = str(uuid.getnode())

GH_OAUTH_CLIENT_ID = ''
GH_OAUTH_CLIENT_SECRET = ''

#BOT_TOKEN = ''

