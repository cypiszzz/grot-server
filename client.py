import http.client
import json
import random
import sys
import time

if __name__ == '__main__':
    token = sys.argv[1]
    game = sys.argv[2]

    time.sleep(random.random())

    client = http.client.HTTPConnection('localhost', 8080)
    client.connect()

    client.request('GET', '/games/{}/board?token={}'.format(game, token))
    response = client.getresponse()

    while response.status == 200:
        data = json.loads(response.read().decode())

        time.sleep(random.random() * 3 + 1)

        client.request(
            'POST', '/games/{}/board?token={}'.format(game, token),
            json.dumps({
                'x': random.randint(0, 4),
                'y': random.randint(0, 4),
            })
        )

        response = client.getresponse()
