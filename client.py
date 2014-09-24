import httplib
import json
import random
import sys
import time

if __name__ == '__main__':
    user = sys.argv[1]
    rand = random.Random(1)

    client = httplib.HTTPConnection('localhost', 8080)
    client.connect()

    client.request('GET', '/games/0/board?user={}'.format(user))
    response = client.getresponse()

    while response.status == 200:
        data = json.load(response)

        time.sleep(random.randint(0, 5))

        client.request(
            'POST', '/games/0/board?user={}'.format(user),
            json.dumps({
                'x': rand.randint(0, 4),
                'y': rand.randint(0, 4),
            })
        )

        response = client.getresponse()
