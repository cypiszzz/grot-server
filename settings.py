import pymongo

db = pymongo.MongoClient().grot

db['users'].ensure_index([
    ('token', pymongo.HASHED),
])
db['users'].ensure_index([
    ('login', pymongo.HASHED),
])


ADMINS = (
    'sargo',
)

GH_OAUTH_CLIENT_ID = ''
GH_OAUTH_CLIENT_SECRET = ''

#BOT_TOKEN = ''

