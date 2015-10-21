import motor
import pymongo
import uuid

DEBUG = True

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

RESULT_LIST = {
    'min_score': 100
}

COOKIE_SECRET = str(uuid.getnode())

GH_OAUTH_CLIENT_ID = '313011c2fb7496cfabde'
GH_OAUTH_CLIENT_SECRET = 'b387156a3321b489b10299d23dea5eef1ef78702'

BOT_TOKEN = 'a1f9c8d7-465b-4aeb-95f2-ddb00f4816df'
