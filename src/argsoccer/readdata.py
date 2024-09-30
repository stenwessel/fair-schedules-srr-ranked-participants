import itertools
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import NewType, Mapping, Iterator

from LeftFairnessMeasure import interval_distance

DATA_DIR: Path = Path('../../res/soccer')

HA = NewType('HA', int)
type Match = tuple[SoccerTeam, SoccerTeam]
type Round = list[Match]
type HAP = list[HA]
type Ranking = list[SoccerTeam]


@dataclass(frozen=True)
class SoccerTeam:
    name: str
    position: int | None

    def __str__(self):
        return f'{self.name}'


def read_participants(file_path: Path) -> Iterator[SoccerTeam]:
    with open(file_path) as f:
        # Skip the header line
        for p, line in enumerate(itertools.islice(f, 0, None)):
            name = line.strip()
            position = p + 1

            yield SoccerTeam(name, position)


def read_round_schedule(r: str, players: Mapping[str, SoccerTeam]) -> Iterator[Match]:
    # Skip header line
    for line in itertools.islice(r.splitlines(), 0, None):
        p, q = map(str.strip, line.split('-', 1))

        # Remove the scores
        q = q.lstrip().split('\t', maxsplit=1)[0].strip()


        yield players[p], players[q]


def read_schedule(file_path: Path, players: Mapping[str, SoccerTeam]) -> Iterator[list[Match]]:
    with open(file_path) as f:
        rounds = f.read().split('\n\n')
        for r in rounds:
            yield list(read_round_schedule(r, players))


@dataclass
class Schedule:
    participants: list[SoccerTeam] = field(repr=False)
    rounds: list[Round] = field(repr=False)
    plays_home: Mapping[tuple[SoccerTeam, SoccerTeam], bool] = field(init=False)

    def __post_init__(self):
        self.plays_home: dict[tuple[SoccerTeam, SoccerTeam], int] = defaultdict(int)
        for r in self.rounds:
            for match in r:
                self.plays_home[match] += 1

    @staticmethod
    def from_data_files(directory: Path) -> 'Schedule':
        participants = list(read_participants(directory / 'ranking.txt'))
        name_to_participants = {p.name: p for p in participants}

        rounds = list(read_schedule(directory / 'schedule.txt', name_to_participants))

        return Schedule(participants, rounds)

    def plays_home_in_round(self, player: SoccerTeam, r: int) -> bool | None:
        match = next((m for m in self.rounds[r] if player in m), None)
        if match is None:
            return None

        return player == match[0]

    def ranking(self) -> Ranking:
        return sorted(self.participants, key=lambda p: p.position)

    def regular_hap(self, player: SoccerTeam) -> HAP:
        return [HA(int(self.plays_home_in_round(player, r))) for r, _ in enumerate(self.rounds)]

    def ranking_hap(self, player: SoccerTeam, ranking: Ranking) -> HAP:
        return [HA(int(self.plays_home[player, i] == 2)) for i in ranking if i != player]

    def interval_fairness(self, ranking: Ranking, *, player: SoccerTeam | None = None) -> float:
        if player is not None:
            n = len(self.participants)
            return interval_distance(self.ranking_hap(player, ranking)) - (n - 2)**2/8

        return sum(self.interval_fairness(ranking, player=p) for p in self.participants)


if __name__ == '__main__':
    s = Schedule.from_data_files(DATA_DIR / 'den2008')

    print(f'{len(s.participants)} teams: {s.interval_fairness(s.ranking())}')
    for t in s.ranking():
        print(f'  {t.name:22}: {s.ranking_hap(t, s.ranking())} -> {s.interval_fairness(s.ranking(), player=t):>4}')

    for i, p in enumerate(s.ranking()):
        print(f'{i+1}. & {p.name} &', end='')
        for round in s.rounds:
            if any(m[0] == p for m in round):
                print(' \whitesq &', end='')
            else:
                print(' \\blacksq &', end='')
        print()

    for i, p in enumerate(s.ranking()):
        print(f'{i+1}. & {p.name} &', end='')
        for p2 in s.ranking():
            if p == p2:
                continue
            if s.plays_home[p, p2] == 2:
                print(' \whitesq &', end='')
            else:
                print(' \\blacksq &', end='')
        print()