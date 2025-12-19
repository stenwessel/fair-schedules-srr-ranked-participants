import itertools
from typing import Iterable, NewType

import gurobipy as gp

from gurobipy import GRB, quicksum

from models.problem import RankingHap

Team = NewType('Team', int)

class SmallestF:
    def __init__(self, n: int) -> None:
        self.n = n

    @property
    def teams(self) -> Iterable[Team]:
        for i in range(self.n):
            yield Team(i)

    @property
    def ranking_haps(self) -> Iterable[tuple[str, ...]]:
        for ha in itertools.product('HA', repeat=self.n - 1):
            yield ha

    def build(self) -> None:
        model = gp.Model()

        x: dict[tuple[Team, tuple[str, ...]], gp.Var] = {
            (i, h): model.addVar(name=f'x[{i},{h}]', vtype=GRB.BINARY, obj=RankingHap(h).f_value() / self.n)
            for i in self.teams
            for h in self.ranking_haps
        }

        for i in self.teams:
            model.addConstr(
                quicksum(x[i, h] for h in self.ranking_haps) == 1
            )

        for i, j in itertools.combinations(self.teams, 2):
            model.addConstr(
                quicksum(x[i, h]
                         for h in self.ranking_haps
                         if h[j - 1] == 'H') ==
                quicksum(x[j, h]
                         for h in self.ranking_haps
                         if h[i] == 'A')
            )

        model.addConstr(
            quicksum(x[i, h]
                     for i in self.teams
                     for h in self.ranking_haps
                     if RankingHap(h).f_value() == 0.06593406593406595) == 2
        )

        model.setParam(GRB.Param.PoolSearchMode, 2)
        model.setParam(GRB.Param.PoolGap, 0)

        self.model = model
        self.x = x

    def optimize(self):
        self.model.optimize()

    def print_solution(self):
        if self.model.status != GRB.OPTIMAL:
            print('No optimal solution found')
            return

        for sol in range(self.model.getAttr(GRB.Attr.SolCount)):
            self.model.setParam(GRB.Param.SolutionNumber, sol)
            for i in self.teams:
                print(f'{i+1:>2}:', end='')
                for h in self.ranking_haps:
                    if self.x[i, h].PoolNX > 0.5:
                        print(''.join(h), '->', RankingHap(h).f_value())

                print()


if __name__ == '__main__':
    # This model can be used to find all ranking HAP sets that have F-value at most the optimal one
    m = SmallestF(14)
    m.build()
    m.optimize()
    m.print_solution()