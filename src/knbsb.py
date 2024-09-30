# Read the data
import itertools
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import NewType

from LeftFairnessMeasure import interval_distance

DATA_DIR: Path = Path('../res/knbsb-hb-hk-2024')

HA = NewType('HA', int)
type HAP = list[HA]
type Ranking = list[str]


@dataclass(frozen=True)
class Team:
    name: str
    rank: int


teams: list[Team] = []

with open(DATA_DIR / 'participants.tsv') as f:
    for line in itertools.islice(f, 1, None):
        rank, name = map(str.strip, line.split('\t', maxsplit=1))
        teams.append(Team(name, int(rank)))

schedule: list[list[tuple[str, str]]] = []
plays_home: dict[tuple[str, str], bool] = defaultdict(bool)

with open(DATA_DIR / 'schedule.txt') as f:
    rounds = f.read().split('\n\n')
    for r in rounds:
        games = []
        for line in itertools.islice(r.splitlines(), 1, None):
            p, q = map(str.strip, line.split('\t', maxsplit=1))
            games.append((p, q))
            plays_home[(p, q)] = True

        schedule.append(games)


def ranking_hap(team: str, ranking: Ranking) -> HAP:
    return [HA(int(plays_home[team, i])) for i in ranking if i != team]


def interval_fairness(ranking: Ranking, *, team: str | None = None) -> float:
    if team is not None:
        n = len(teams)
        return interval_distance(ranking_hap(team, ranking)) - 6  # TODO: hardcoded for 9 teams!

    return sum(interval_fairness(ranking, team=t.name) for t in teams)


rankings = [
    ('HS+Vervolgcompetitie', [t.name for t in sorted(teams, key=lambda t: t.rank)]),
    ('Reguliere Competitie', ['NEP', 'HCA', 'AMS', 'RCH', 'TWI', 'DKH', 'PIO', 'QUI', 'UVV']),
    ('HS+Reguliere competitie', ['AMS', 'NEP', 'HCA', 'RCH', 'TWI', 'DKH', 'PIO', 'QUI', 'UVV']),
]

ideal = [1, 0, 1, 0, 1, 0, 1, 0]
ideal2 = [0, 1, 0, 1, 0, 1, 0, 1]
print(f'Ideal: {ideal} -> {interval_distance(ideal) - 6:>4}')
print(f'       {ideal2} -> {interval_distance(ideal2) - 6:>4}')
print()

for n, r in rankings:
    print(f'\nRanking {n + ':':26} {interval_fairness(r):>4}')
    for t in r:
        print(f'  {t}: {ranking_hap(t, r)} -> {interval_fairness(r, team=t):>4}')