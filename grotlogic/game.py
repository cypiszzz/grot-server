class Game(object):

    def __init__(self, board):
        self.board = board
        self.score = 0
        self.moves = 5

    def start_move(self, x, y):
        """
        Set initial values and start chain reaction.
        """
        field = self.board.get_field(x, y)
        self.moves -= 1

        self.move_score = 0
        self.move_length = 0

        self.move_next_field(field)

    def skip_move(self):
        """
        Skip the move
        """
        self.moves -= 1

    def move_next_field(self, start_field):
        """
        One step in chain reaction.
        """
        next_field = self.board.get_next_field(start_field)
        start_field.direction = None
        self.move_score += start_field.points
        self.move_length += 1

        if next_field is None:
            self.finish_move()
        else:
            self.move_next_field(next_field)

    def update_score(self):
        """
        Update game score.
        """
        self.score += self.move_score
        threshold = (self.score // (5 * self.board.size ** 2))
        threshold += self.board.size - 1

        if self.move_length > threshold:
            self.moves += self.move_length - threshold

    def finish_move(self):
        """
        Finish the move.
        """
        self.move_score += self.board.get_extra_points()

        self.board.lower_fields()
        self.board.fill_empty_fields()

        self.update_score()

    def get_state(self, board=True):
        """
        Get the status of the game.
        """
        return {
            'score': self.score,
            'moves': self.moves,
            'board': self.board.get_state() if board else None,
        }

    def is_active(self):
        """
        Return whether the game is still active or not.
        """
        return self.moves > 0
