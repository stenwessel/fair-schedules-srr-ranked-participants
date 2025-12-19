import itertools
from collections import deque
from typing import NewType, Iterator

Player = NewType('Player', int)
Round = NewType('Round', int)
BreakPattern = NewType('BreakPattern', tuple[int, str])


class FairSrrProblem:
    def __init__(self, n_teams: int, break_gaps: tuple[int, ...] | None = None):
        assert n_teams > 0, 'number of teams must be positive'
        assert n_teams % 2 == 0, 'number of teams must be even'

        if break_gaps is not None:
            assert len(break_gaps) == n_teams // 2
            assert sum(break_gaps) == n_teams - 1

        self.n = n_teams
        self.break_gaps = break_gaps

    @property
    def players(self) -> Iterator[Player]:
        yield from (Player(i) for i in range(self.n))

    @property
    def rounds(self) -> Iterator[Round]:
        yield from (Round(r) for r in range(self.n - 1))

    @property
    def break_patterns(self) -> Iterator[BreakPattern]:
        for r in self.break_rounds:
            for ha in ('H', 'A'):
                yield BreakPattern((r, ha))

    def tight_order_break_patterns(self) -> Iterator[BreakPattern]:
        home = True

        for r, d in zip(
            itertools.chain(self.break_rounds, self.break_rounds),
            itertools.chain((0,), self.break_gaps, self.break_gaps)
        ):
            if d % 2 == 1:
                home = not home
            yield BreakPattern((r, 'H' if home else 'A'))

    @property
    def break_rounds(self) -> Iterator[Round]:
        if self.break_gaps is None:
            yield from self.rounds
            return

        # Fix a break on round 0, and follow the break gaps
        for r in itertools.accumulate(self.break_gaps[:-1], initial=0):
            yield Round(r)

    def pattern(self, p: BreakPattern) -> str:
        break_round, break_type = p
        other = 'A' if break_type == 'H' else 'H'

        m = self.n - 1 - 3
        d = deque(break_type * 2 + other + ''.join(val for pair in zip(break_type * m, other * m) for val in pair))
        d.rotate(break_round - 1)

        return ''.join(d)[:self.n-1]

    def plays_home(self, p: BreakPattern, r: Round) -> bool:
        pattern = self.pattern(p)

        return pattern[r] == 'H'

    def plays_home_against(self, i: Player, j: Player) -> bool:
        return abs(j - i) % 2 == int(i < j)

    def opponents(self, i: Player) -> Iterator[Player]:
        yield from (p for p in self.players if p != i)

    def next_opponent(self, i: Player, j: Player) -> Player | None:
        j_next = (j + 1) if i != j + 1 else (j + 2)

        if j_next >= self.n:
            return None

        return Player(j_next)

    def prev_opponent(self, i: Player, j: Player) -> Player | None:
        j_next = (j - 1) if i != j - 1 else (j - 2)

        if j_next < 0:
            return None

        return Player(j_next)


class RankingHap:
    def __init__(self, hap: tuple[str, ...]):
        self.hap = hap

    def complement(self) -> 'RankingHap':
        return RankingHap(tuple('H' if h == 'A' else 'A' for h in self.hap))

    def f_measure_counted_twice(self) -> int:
        string = [1 if h == 'H' else 0 for h in self.hap]

        n = len(string)
        r = 0
        for i in range(n):
            for j in range(i + 2, n + 1):
                r += abs(2 * sum(string[i:j]) - (j - i))

        return r

    def delta_t(self) -> float:
        return self.f_measure_counted_twice() / 2

    def f_value(self) -> float:
        n = len(self.hap) + 1
        return (self.delta_t() - (n-2)**2 / 8) / (1/24 * n * (n - 1) * (n - 2))

    def __str__(self):
        return ''.join(self.hap)
