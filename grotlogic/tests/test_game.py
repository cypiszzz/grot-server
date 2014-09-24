from unittest import TestCase

from ..game import Game
from .utils import assert_fields_directions, set_fields_directions


class GameTestCase(TestCase):

    def setUp(self):
        self.game = Game(5, 0)

    def test_new_game_is_clean(self):
        self.assertEqual(self.game.moves, 5)
        self.assertEqual(self.game.score, 0)

    def test_skip_move(self):
        moves = self.game.moves
        self.game.skip_move()

        self.assertEqual(self.game.moves, moves - 1)
        self.assertEqual(self.game.score, 0)

    def test_simple_move(self):
        set_fields_directions(
            self.game.board,
            '''
            >v>^>
            v^v>>
            vv<>>
            >>^>^
            >^<v^
            '''
        )

        moves = self.game.moves
        self.game.start_move(0, 0)

        assert_fields_directions(
            self.game.board,
            '''
            XX>^>
            vXv>>
            vv<>>
            >>^>^
            >^<v^
            '''
        )
        self.assertEqual(self.game.moves, moves - 1)
        self.assertEqual(self.game.score, 3)
        self.assertEqual(self.game.move_length, 3)

    def test_complex_move_through_gaps(self):
        set_fields_directions(
            self.game.board,
            '''
            >v>^>
            v^v>>
            vv<>>
            >>^>^
            >^<v^
            '''
        )

        # setting points for a field that will be hit
        self.game.board.get_field(2, 2).points = 4

        # setting points for a fields that will not change
        self.game.board.get_field(4, 4).points = 8
        self.game.board.get_field(2, 4).points = 8
        self.game.board.get_field(0, 0).points = 8

        # setting points for fields that will change,
        # but not because of being hit
        self.game.board.get_field(1, 0).points = 6
        self.game.board.get_field(4, 1).points = 6
        self.game.board.get_field(2, 1).points = 6

        moves = self.game.moves
        self.game.start_move(2, 3)

        assert_fields_directions(
            self.game.board,
            '''
            >XXXX
            vXX^X
            vv>>>
            >^v>>
            >^<v^
            '''
        )
        # Extra three moves for long move
        self.assertEqual(self.game.moves, moves + 2)
        # 6 arrows for 1 point and 1 arrow for 4 points = 10 extra points
        self.assertEqual(self.game.score, 10)
        self.assertEqual(self.game.move_length, 7)

    def test_score_is_properly_added(self):
        set_fields_directions(
            self.game.board,
            '''
            <^^<<
            v^vv>
            ^v<v>
            >^<>^
            >^vv^
            '''
        )

        self.game.start_move(2, 2)
        self.game.board.get_field(4, 2).points = 2

        assert_fields_directions(
            self.game.board,
            '''
            <XX<<
            vX^v>
            ^Xvv>
            >X<>^
            >^vv^
            '''
        )
        # 5 arrows hit = 5 extra points
        self.assertEqual(self.game.score, 5)

        self.game.start_move(3, 3)

        assert_fields_directions(
            self.game.board,
            '''
            <XXXX
            vX^<X
            ^Xvv<
            >X<v>
            >^vv^
            '''
        )
        # 2 arrows for 1 point and 1 for 2 points hit = 4 extra points
        self.assertEqual(self.game.score, 9)

    def test_clearing_vertical_lines(self):
        set_fields_directions(
            self.game.board,
            '''
            <^^<<
            v^vv>
            ^v<v>
            >v<>^
            >^vv^
            '''
        )

        self.game.board.get_field(1, 3).points = 4
        self.game.start_move(1, 2)

        assert_fields_directions(
            self.game.board,
            '''
            <X^<<
            vXvv>
            ^X<v>
            >X<>^
            >Xvv^
            '''
        )
        self.assertEqual(self.game.score, 58)

    def test_clearing_horizontal_lines(self):
        set_fields_directions(
            self.game.board,
            '''
            <^^<<
            v^vv>
            ><<<>
            >v<>^
            >^vv^
            '''
        )

        self.game.board.get_field(0, 2).points = 7
        self.game.start_move(3, 2)

        assert_fields_directions(
            self.game.board,
            '''
            XXXXX
            <^^<<
            v^vv>
            >v<>^
            >^vv^
            '''
        )
        self.assertEqual(self.game.score, 61)
