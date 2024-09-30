import itertools


def cumsum(lis):
    total = 0
    for x in lis:
        total += x
        yield total


def left_fairness_individual(plays_home: dict[tuple[int, int], int], seeding_position: list[int], player: int) -> float:
    n = len(seeding_position)

    opponents = [i for i in range(n) if i != player]
    home_opponents = [1 if plays_home[seeding_position[player], seeding_position[i]] else 0 for i in opponents]
    ideal_home = [i / 2 for i in range(1, n)]

    r = sum(abs(i - j) for i, j in zip(cumsum(home_opponents), ideal_home)) - n / 4
    print(f'{home_opponents} -> {r}')
    return r


def left_fairness_tournament(plays_home: dict[tuple[int, int], int], seeding_position: list[int]) -> float:
    return sum(left_fairness_individual(plays_home, seeding_position, p) for p in range(len(seeding_position)))


def count_breaks_ind(plays_home: dict[tuple[int, int], int], seeding_position: list[int], player: int) -> int:
    n = len(seeding_position)

    opponents = [i for i in range(n) if i != player]
    home_opponents = [1 if plays_home[seeding_position[player], seeding_position[i]] else 0 for i in opponents]

    r = sum(i == j for i, j in itertools.pairwise(home_opponents))
    print(f'{home_opponents} -> {r}')
    return r


def count_breaks_tmt(plays_home: dict[tuple[int, int], int], seeding_position: list[int]) -> int:
    return sum(count_breaks_ind(plays_home, seeding_position, p) for p in range(len(seeding_position)))


def interval_distance(string: list[int]) -> float:
    n = len(string)
    r = 0
    for i in range(n):
        for j in range(i + 2, n + 1):
            r += abs(sum(string[i:j]) - (j - i)/2)
            # print(f'{i}--{j-1} {string[i:j]} -> {abs(sum(string[i:j]) - (j - i)/2)}')
            # if (j - i) % 2 == 1:
            #     r -= 1/2

    return r


def interval_ind(plays_home: dict[tuple[int, int], int], seeding_position: list[int], player: int) -> float:
    n = len(seeding_position)

    opponents = [i for i in range(n) if i != player]
    home_opponents = [1 if plays_home[seeding_position[player], seeding_position[i]] else 0 for i in opponents]

    r = interval_distance(home_opponents) - (n - 2)**2/8
    print(f'{home_opponents} -> {r}')
    return r


def interval_tmt(plays_home: dict[tuple[int, int], int], seeding_position: list[int]) -> float:
    return sum(interval_ind(plays_home, seeding_position, p) for p in range(len(seeding_position)))
