DIRECTION_MAP = {
    '<': 'left',
    '>': 'right',
    '^': 'up',
    'v': 'down',
    'O': None,
}


def set_fields_directions(board, field_map, start=0, end=None):
    rows = [row.strip() for row in field_map.strip().split('\n')]
    end = board.size if end is None else end

    if len(rows) != end - start:
        raise ValueError('Invalid field map height!')

    for y in range(start, end):
        row = rows[y]

        if len(row) != board.size:
            raise ValueError('Invalid field map width for row {}!'.format(y))

        for x in range(board.size):
            direction = DIRECTION_MAP.get(row[x])

            field = board.get_field(x, y)
            field.direction = direction
            field.points = 1


def assert_fields_directions(board, field_map, start=0, end=None):
    rows = [row.strip() for row in field_map.strip().split('\n')]
    end = board.size if end is None else end

    if len(rows) != end - start:
        raise ValueError('Invalid field map height!')

    for y in range(start, end):
        row = rows[y]

        if len(row) != board.size:
            raise ValueError('Invalid field map width for row {}!'.format(y))

        for x in range(board.size):
            field = board.get_field(x, y)

            assert field.direction in DIRECTION_MAP.values(), \
                "Direction invalid ({}) at {},{}".format(
                    field.direction,
                    field.x,
                    field.y,
                )

            if row[x] == 'X':
                assert field.direction is not None, \
                    "Direction is None at {},{}".format(
                        field.x,
                        field.y,
                    )
                continue

            direction = DIRECTION_MAP.get(row[x])
            assert field.direction == direction, \
                "Direction {} != {} at {},{}".format(
                    field.direction,
                    direction,
                    field.x,
                    field.y,
                )
