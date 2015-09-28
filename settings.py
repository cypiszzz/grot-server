import pymongo


ADMINS = (
    'sargo',
)

GH_OAUTH_CLIENT_ID = ''
GH_OAUTH_CLIENT_SECRET = ''

db = pymongo.MongoClient().grot

db['users'].ensure_index([
    ('token', pymongo.HASHED),
])
db['users'].ensure_index([
    ('login', pymongo.HASHED),
])

db['duels'].ensure_index([
    ('players.rating', pymongo.DESCENDING),
])
