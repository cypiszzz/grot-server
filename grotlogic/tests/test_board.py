from unittest import TestCase

from ..board import Board
from .utils import assert_fields_directions, set_fields_directions


class BoardTestCase(TestCase):

    def setUp(self):
        self.board = Board(5, 0)

    def test_get_field(self):
        for x in range(self.board.size):
            for y in range(self.board.size):
                field = self.board.get_field(x, y)
                self.assertEqual(field.x, x)
                self.assertEqual(field.y, y)

    def test_empty_lines(self):
        set_fields_directions(
            self.board,
            '''
            >v>^>
            vOO>>
            OOOOO
            >OO>O
            >OOv^
            '''
        )

        self.assertEqual(self.board.get_extra_points(), 50)

        set_fields_directions(self.board, '>vO^>', end=1)
        self.assertEqual(self.board.get_extra_points(), 100)

        set_fields_directions(self.board, '>OO^>', end=1)
        self.assertEqual(self.board.get_extra_points(), 150)

    def test_get_next_field(self):
        set_fields_directions(
            self.board,
            '''
            >vv^v
            >>O<v
            >OOO>
            v^>v<
            <>v>^
            '''
        )

        # going right
        field = self.board.get_field(0, 0)
        next_field = self.board.get_next_field(field)
        self.assertEqual(next_field.x, 1)
        self.assertEqual(next_field.y, 0)

        # going left
        field = self.board.get_field(4, 3)
        next_field = self.board.get_next_field(field)
        self.assertEqual(next_field.x, 3)
        self.assertEqual(next_field.y, 3)

        # going up
        field = self.board.get_field(4, 4)
        next_field = self.board.get_next_field(field)
        self.assertEqual(next_field.x, 4)
        self.assertEqual(next_field.y, 3)

        # going down
        field = self.board.get_field(4, 1)
        next_field = self.board.get_next_field(field)
        self.assertEqual(next_field.x, 4)
        self.assertEqual(next_field.y, 2)

        # going right out of map
        field = self.board.get_field(4, 2)
        next_field = self.board.get_next_field(field)
        self.assertEqual(next_field, None)

        # going left out of map
        field = self.board.get_field(0, 4)
        next_field = self.board.get_next_field(field)
        self.assertEqual(next_field, None)

        # going up out of map
        field = self.board.get_field(3, 0)
        next_field = self.board.get_next_field(field)
        self.assertEqual(next_field, None)

        # going down out of map
        field = self.board.get_field(4, 2)
        next_field = self.board.get_next_field(field)
        self.assertEqual(next_field, None)

        # going left through a gap
        field = self.board.get_field(0, 2)
        next_field = self.board.get_next_field(field)
        self.assertEqual(next_field.x, 4)
        self.assertEqual(next_field.y, 2)

        # going right through a gap
        field = self.board.get_field(3, 1)
        next_field = self.board.get_next_field(field)
        self.assertEqual(next_field.x, 1)
        self.assertEqual(next_field.y, 1)

        # going up through a gap
        field = self.board.get_field(1, 3)
        next_field = self.board.get_next_field(field)
        self.assertEqual(next_field.x, 1)
        self.assertEqual(next_field.y, 1)

        # going down through a gap
        field = self.board.get_field(2, 0)
        next_field = self.board.get_next_field(field)
        self.assertEqual(next_field.x, 2)
        self.assertEqual(next_field.y, 3)

    def test_lower_fields(self):
        set_fields_directions(
            self.board,
            '''
            >vvOO
            >>OOO
            >OO>O
            v^>OO
            <OvOO
            '''
        )
        self.board.lower_fields()
        assert_fields_directions(
            self.board,
            '''
            >OOOO
            >OOOO
            >vvOO
            v>>OO
            <^v>O
            '''
        )

    def test_fill_empty_fields(self):
        set_fields_directions(
            self.board,
            '''
            >OOOO
            >OOOO
            >vvOO
            v>>OO
            <^v>O
            '''
        )

        self.board.fill_empty_fields()
        assert_fields_directions(
            self.board,
            '''
            >XXXX
            >XXXX
            >vvXX
            v>>XX
            <^v>X
            '''
        )

    def test_get_state(self):
        board = Board(3, 0)
        self.assertEqual(
            board.get_state(),
            [
                [
                    board.get_field(0, 0).get_state(),
                    board.get_field(1, 0).get_state(),
                    board.get_field(2, 0).get_state(),
                ],
                [
                    board.get_field(0, 1).get_state(),
                    board.get_field(1, 1).get_state(),
                    board.get_field(2, 1).get_state(),
                ],
                [
                    board.get_field(0, 2).get_state(),
                    board.get_field(1, 2).get_state(),
                    board.get_field(2, 2).get_state(),
                ],
            ],
        )
