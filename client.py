import http.client
import json
import random
import sys
import time

if __name__ == '__main__':
    token = sys.argv[1]
    rand = random.Random(1)

    time.sleep(random.random())

    client = http.client.HTTPConnection('localhost', 8080)
    client.connect()

    client.request('GET', '/games/1/board?token={}'.format(token))
    response = client.getresponse()

    while response.status == 200:
        data = json.loads(response.read().decode())

        time.sleep(random.random() * 3 + 1)

        client.request(
            'POST', '/games/1/board?token={}'.format(token),
            json.dumps({
                'x': rand.randint(0, 4),
                'y': rand.randint(0, 4),
            })
        )

        response = client.getresponse()
