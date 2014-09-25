import random

from .field import Field


class Board(object):

    def __init__(self, size, seed):
        self.size = size
        self.seed = seed
        self.random = random.Random(seed)

        self.fields = [
            [Field(x, y, self.random) for x in range(size)]
            for y in range(size)
        ]

    def __copy__(self):
        return Board(self.size, self.seed)

    def get_field(self, x, y):
        """
        Returns the field at the given coordinates.
        """
        return self.fields[y][x]

    def get_next_field(self, field, direction=None):
        """
        Returns next field in chain reaction and information is it last step
        in this chain reaction.
        """
        direction = field.direction or direction

        if direction == 'left':
            if field.x == 0:
                return None
            next_field = self.get_field(field.x - 1, field.y)

        elif direction == 'right':
            if field.x == (self.size - 1):
                return None
            next_field = self.get_field(field.x + 1, field.y)

        elif direction == 'up':
            if field.y == 0:
                return None
            next_field = self.get_field(field.x, field.y - 1)

        elif direction == 'down':
            if field.y == (self.size - 1):
                return None
            next_field = self.get_field(field.x, field.y + 1)

        if next_field.direction is None:
            # if next was alread cleared than go further in the same direction
            return self.get_next_field(next_field, direction)

        return next_field

    def lower_field(self, field):
        """
        When chain reaction is over fields that are 'flying' should be lowered.
        """
        new_y = field.y
        while new_y < self.size - 1:
            if self.get_field(field.x, new_y + 1).direction is not None:
                # next field below is not empty, so finish lowering
                break
            new_y += 1

        if new_y != field.y:
            next_field = self.get_field(field.x, new_y)
            # swap fields values
            field.points, next_field.points = next_field.points, field.points
            field.direction, next_field.direction = next_field.direction, field.direction

    def lower_fields(self):
        """
        Lower fields (use gravity).
        """
        for y in reversed(range(self.size - 1)):
            for x in range(self.size):
                self.lower_field(self.get_field(x, y))

    def fill_empty_fields(self):
        """
        Reset fields in empty places.
        """
        for x in range(self.size):
            for y in range(self.size):
                field = self.get_field(x, y)
                if field.direction is None:
                    field.reset()

    def get_extra_points(self):
        """
        Return extra points for the empty rows and columns.
        """
        extra_points = 0

        for x in range(self.size):
            is_empty = True
            for y in range(self.size):
                if self.get_field(x, y).direction is not None:
                    is_empty = False
                    break

            if is_empty:
                extra_points += self.size * 10

        for y in range(self.size):
            is_empty = True
            for x in range(self.size):
                if self.get_field(x, y).direction is not None:
                    is_empty = False
                    break

            if is_empty:
                extra_points += self.size * 10

        return extra_points

    def get_state(self):
        """
        Get the status of the board.
        """
        rows = []
        for y in range(self.size):
            row = []
            for x in range(self.size):
                row.append(self.get_field(x, y).get_state())
            rows.append(row)
        return rows
