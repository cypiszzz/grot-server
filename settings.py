import pymongo

SMTP_HOST = 'smtp.gmail.com:587'
SMTP_EMAIL = 'gorottest@gmail.com'
SMTP_PASSWORD = 'lolol123'

db = pymongo.MongoClient().grot

db['users'].ensure_index([
    ('token', pymongo.HASHED),
])

db['duels'].ensure_index([
    ('players.rating', pymongo.DESCENDING),
])
