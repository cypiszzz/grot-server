POINTS = [1, 1, 1, 1, 2, 2, 2, 3, 3, 4]
DIRECTIONS = ['up', 'down', 'right', 'left']


class Field(object):
    """
    Holds field state.
    """

    def __init__(self, x, y, random):
        self.x = x
        self.y = y
        self.random = random
        self.reset()

    def reset(self):
        self.points = self.random.choice(POINTS)
        self.direction = self.random.choice(DIRECTIONS)

    def get_state(self):
        return {
            'points': self.points,
            'direction': self.direction,
            'x': self.x,
            'y': self.y,
        }
