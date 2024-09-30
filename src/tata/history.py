import itertools
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Mapping, NewType, Iterable, Callable

from LeftFairnessMeasure import interval_distance

DATA_DIR: Path = Path('../../res/tatachess')
EXCLUDED: set[int] = {1993, 1995, 1981}
YEARS: list[int] = [y for y in range(1971, 2024) if y not in EXCLUDED]

HA = NewType('HA', int)
type Match = tuple[ChessPlayer, ChessPlayer]
type Round = list[Match]
type HAP = list[HA]
type Ranking = list[ChessPlayer]


@dataclass(frozen=True)
class ChessPlayer:
    name: str
    country: str
    rating: int
    position: int | None

    def __str__(self):
        return f'{self.name} ({self.country})'


def normalize_name(name: str) -> str:
    if 'Dr.' in name:
        name = name.replace('Dr.', '').strip()

    name = name.replace('.', '')
    name = ' '.join(p for p in name.split(' ') if len(p) > 1)

    if name.startswith('R, ') or name.startswith('D, '):
        name = name[3:]

    return name


def read_participants(file_path: Path) -> Iterator[ChessPlayer]:
    with open(file_path) as f:
        # Skip the header line
        for line in itertools.islice(f, 1, None):
            name, country, rating, position = map(str.strip, line.split('\t'))
            position = int(position) if position != '?' else None
            rating = int(rating)

            if ',' not in name:
                first, last = name.split(' ', 1)
                name = f'{last}, {first}'

            yield ChessPlayer(normalize_name(name), country, rating, position)


def read_round_schedule(r: str, players: Mapping[str, ChessPlayer]) -> Iterator[Match]:
    # Skip header line
    for line in itertools.islice(r.splitlines(), 1, None):
        p, q = map(str.strip, line[:-3].split('-', 1))

        yield players[normalize_name(p)], players[normalize_name(q)]


def read_schedule(file_path: Path, players: Mapping[str, ChessPlayer]) -> Iterator[list[Match]]:
    with open(file_path) as f:
        rounds = f.read().split('\n\n')
        for r in rounds:
            yield list(read_round_schedule(r, players))


def all_rankings[T, R](players: Iterable[T], key: Callable[[T], R], descending: bool = False) -> Iterator[list[T]]:
    base = sorted(players, key=key, reverse=descending)
    groups = [itertools.permutations(list(g[1])) for g in itertools.groupby(base, key=key)]
    for r in itertools.product(*groups):
        yield [p for group in r for p in group]


@dataclass
class Schedule:
    year: int
    participants: list[ChessPlayer] = field(repr=False)
    rounds: list[Round] = field(repr=False)
    plays_home: Mapping[tuple[ChessPlayer, ChessPlayer], bool] = field(init=False)

    def __post_init__(self):
        self.plays_home: dict[tuple[ChessPlayer, ChessPlayer], bool] = defaultdict(bool)
        for r in self.rounds:
            for match in r:
                self.plays_home[match] = True

    @staticmethod
    def from_data_files(directory: Path) -> 'Schedule':
        participants = list(read_participants(directory / 'participants.tsv'))
        name_to_participants = {p.name: p for p in participants}

        rounds = list(read_schedule(directory / 'schedule.txt', name_to_participants))

        return Schedule(int(directory.name), participants, rounds)

    def rankings(self) -> Iterator[Ranking]:
        if not any(not p.position for p in self.participants):
            # Order by position in the world ranking
            yield from all_rankings(self.participants, lambda p: p.position)
        else:
            yield from all_rankings(self.participants, lambda p: p.rating, descending=True)

    def plays_home_in_round(self, player: ChessPlayer, r: int) -> bool | None:
        match = next((m for m in self.rounds[r] if player in m), None)
        if match is None:
            return None

        return player == match[0]

    def regular_hap(self, player: ChessPlayer) -> HAP:
        return [HA(int(self.plays_home_in_round(player, r))) for r, _ in enumerate(self.rounds)]

    def ranking_hap(self, player: ChessPlayer, ranking: Ranking) -> HAP:
        return [HA(int(self.plays_home[player, i])) for i in ranking if i != player]

    def interval_fairness(self, ranking: Ranking, *, player: ChessPlayer | None = None) -> float:
        if player is not None:
            n = len(self.participants)
            return interval_distance(self.ranking_hap(player, ranking)) - (n - 2)**2/8

        return sum(self.interval_fairness(ranking, player=p) for p in self.participants)


if __name__ == '__main__':
    tournaments = {year: Schedule.from_data_files(DATA_DIR / str(year)) for year in YEARS}

    for y in YEARS:
        t = tournaments[y]
        print(f'{t.year} ({len(t.participants)} players): {", ".join(str(t.interval_fairness(r)) for r in t.rankings())}')

    print('\n2002 ranking with 731:')
    t_2002 = tournaments[2002]
    r = list(t_2002.rankings())[1]
    for p in r:
        print(f'{p.name:21} ({p.rating}): {t_2002.ranking_hap(p, r)} -> {t_2002.interval_fairness(r, player=p)}')


    for i, p in enumerate(r):
        print(f'{i+1}. & {p.name.split(",")[0]} &', end='')
        for round in t_2002.rounds:
            if any(m[0] == p for m in round):
                print(' W &', end='')
            else:
                print(' B &', end='')
        print()

    for i, p in enumerate(r):
        print(f'{i+1}. & {p.name.split(",")[0]} &', end='')
        for p2 in r:
            if p == p2:
                continue
            if t_2002.plays_home[p, p2]:
                print(' \whitesquare &', end='')
            else:
                print(' \blacksquare &', end='')
        print()

    for i, round in enumerate(t_2002.rounds, start=1):
        print('\\multicolumn{3}{l}{\\textbf{Round ' + str(i) + '}} \\\\')
        for j, match in enumerate(round):
            print(f'{match[0].name.split(",")[0]} & -~ & {match[1].name.split(",")[0]} \\\\{"[1ex]" if j == 6 else ""}')