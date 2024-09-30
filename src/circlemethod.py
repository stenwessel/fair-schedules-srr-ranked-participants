import pprint
from itertools import islice


def circle_method(n: int) -> list[list[tuple[int, int]]]:
    """
    Generates a single round robin schedule with the circle method.

    This places the last team in the center of the circle (the fixed player), the others are placed in counterclockwise
    order, where the last player plays the first player in the first round.

    The generated schedules are equivalent to the Berger tables.

    :param n: The number of players, must be even.
    :return: A list of rounds, where every round contains a list of matches of the form (i, j), indicating that
    i plays j at home.
    """
    assert n > 0
    assert n % 2 == 0

    nrounds = n - 1
    rounds = []

    fixed_player = n - 1
    deque = list(range(n - 1))

    for r in range(nrounds):
        left, right = deque[:n // 2], deque[n // 2:]
        matches = [(deque[0], fixed_player) if r % 2 == 0 else (fixed_player, deque[0])]
        matches.extend(zip(islice(left, 1, None), reversed(right)))

        rounds.append(matches)

        deque = right + left

    return rounds


if __name__ == '__main__':
    pprint.pprint(circle_method(14))