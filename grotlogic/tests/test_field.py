from random import Random
from unittest import TestCase

from ..field import Field


class FieldTestCase(TestCase):

    def setUp(self):
        self.random = Random()
        self.field = Field(0, 0, self.random)

    def test_reset(self):
        points = set([1, 2, 3, 4])
        directions = set(['left', 'right', 'up', 'down'])

        used_points = set()
        used_directions = set()

        for i in range(1000):
            self.field.reset()

            used_points.add(self.field.points)
            used_directions.add(self.field.direction)

            unused_points = len(points - used_points)
            unused_directions = len(directions - used_directions)

            if not unused_points and not unused_directions:
                break

        self.assertTrue(not unused_points and not unused_directions)

    def test_reset_uses_provided_random(self):
        def get_states_for_seed(seed):
            field = Field(0, 0, Random(seed))
            states = []
            for i in range(100):
                field.reset()
                states.append(field.get_state())
            return states

        states1 = get_states_for_seed(0.3)
        states2 = get_states_for_seed(0.3)
        states3 = get_states_for_seed(0.3)
        states4 = get_states_for_seed(0.4)
        states5 = get_states_for_seed(0.4)
        states6 = get_states_for_seed(0.4)

        self.assertEqual(states1, states2)
        self.assertEqual(states2, states3)
        self.assertEqual(states4, states5)
        self.assertEqual(states5, states6)
        self.assertNotEqual(states1, states4)

    def test_get_state(self):
        self.field.points = 4
        self.field.direction = 'right'
        self.assertDictEqual(
            self.field.get_state(),
            {'points': 4, 'direction': 'right', 'x': 0, 'y': 0},
        )

        self.field.points = 42
        self.field.direction = 'foo'
        self.assertDictEqual(
            self.field.get_state(),
            {'points': 42, 'direction': 'foo', 'x': 0, 'y': 0},
        )
