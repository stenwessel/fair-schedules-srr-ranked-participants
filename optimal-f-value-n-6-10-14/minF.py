import itertools

import gurobipy as gp
from gurobipy import GRB

from models.problem import FairSrrProblem, Player, Round, BreakPattern, RankingHap


class MinRankingFairnessModel:
    def __init__(self, problem: FairSrrProblem, ranking_hap_set: list[str] | None, bandwidth: bool = False):
        self.problem = problem
        self.ranking_hap_set = ranking_hap_set
        self.bandwidth = bandwidth
        self._build()

    def _build(self):
        model = gp.Model()
        model.setAttr(GRB.Attr.ModelSense, GRB.MINIMIZE)

        # If bandwidth model: model an f_min and f_max
        if self.bandwidth:
            f_min = model.addVar(vtype=GRB.CONTINUOUS, name='f_min', obj=-1)
            f_max = model.addVar(vtype=GRB.CONTINUOUS, name='f_max', obj=1)

        # x[i, j, r] == 1 iff i plays j at home in round r
        x: dict[tuple[Player, Player, Round], gp.Var] = {
            (i, j, r): model.addVar(vtype=GRB.BINARY, name=f'x[{i},{j},{r}]')
            for i, j in itertools.product(self.problem.players, self.problem.players)
            if i != j
            for r in self.problem.rounds
        }

        # b[i, p] == 1 iff i gets assigned break pattern p
        b: dict[tuple[Player, BreakPattern], gp.Var] = {
            (i, p): model.addVar(vtype=GRB.BINARY, name=f'b[{i},{p}]')
            for i in self.problem.players
            for p in self.problem.break_patterns
        }

        # Every player is assigned exactly one pattern
        for i in self.problem.players:
            model.addConstr(
                gp.quicksum(b[i, p] for p in self.problem.break_patterns) == 1
            )

        # SRR: play every opponent exactly once
        for i, j in itertools.combinations(self.problem.players, 2):
            model.addConstr(
                gp.quicksum(x[i, j, r] + x[j, i, r] for r in self.problem.rounds) == 1
            )

        # SRR: play exactly once in every round
        for i in self.problem.players:
            for r in self.problem.rounds:
                model.addConstr(
                    gp.quicksum(x[i, j, r] + x[j, i, r] for j in self.problem.opponents(i)) == 1
                )

        # Make sure that the break pattern matches the home/away assignment
        for i in self.problem.players:
            for r in self.problem.rounds:
                model.addConstr(
                    gp.quicksum(x[i, j, r] for j in self.problem.opponents(i)) == gp.quicksum(b[i, p] for p in self.problem.break_patterns if self.problem.plays_home(p, r))
                )

        # Model F measure
        # z[p, i, j] = |H^t_{i,j} - (j - i + 1)/2|
        z: dict[tuple[Player, int, int], gp.Var] = {
            (p, i, j): model.addVar(vtype=GRB.CONTINUOUS, name=f'z[{p},{i},{j}]', obj=1)
            for p in self.problem.players
            for i in range(self.problem.n)
            for j in range(i + 2, self.problem.n)
        }

        if self.bandwidth:
            z_sign: dict[tuple[Player, int, int], gp.Var] = {
                (p, i, j): model.addVar(vtype=GRB.BINARY, name=f'z_sign[{p},{i},{j}]')
                for p in self.problem.players
                for i in range(self.problem.n)
                for j in range(i + 2, self.problem.n)
            }

        for p in self.problem.players:
            for i in range(self.problem.n):
                for j in range(i + 2, self.problem.n):
                    h_p_ij = gp.quicksum(x[p, q, r] for r in self.problem.rounds for q in list(self.problem.opponents(p))[i:j])
                    diff = 2*h_p_ij - (j - i)

                    if self.bandwidth:
                        model.addConstr((z_sign[p, i, j] == 1) >> (z[p, i, j] == diff))
                        model.addConstr((z_sign[p, i, j] == 0) >> (z[p, i, j] == -diff))
                    else:
                        model.addConstr(z[p, i, j] >= diff)
                        model.addConstr(z[p, i, j] >= -diff)

        if self.bandwidth:
            for p in self.problem.players:
                model.addConstr(
                    gp.quicksum(z[p, i, j] for i in range(self.problem.n) for j in range(i + 2, self.problem.n)) <= f_max
                )
                model.addConstr(
                    gp.quicksum(z[p, i, j] for i in range(self.problem.n) for j in range(i + 2, self.problem.n)) >= f_min
                )

        # Enforce ranking HAP
        if self.ranking_hap_set is not None:
            for i, ranking_hap in enumerate(self.ranking_hap_set):
                for j, ha in zip(self.problem.opponents(i), ranking_hap):
                    model.addConstr(
                        gp.quicksum(x[i, j, r] for r in self.problem.rounds) == (1 if ha == 'H' else 0)
                    )

        self.model = model
        self.x = x
        self.b = b

    def optimize(self):
        self.model.optimize()

    def print_schedule_rounds(self):
        print("========= Rounds =========")
        for r in self.problem.rounds:
            print(f'R {r+1:>2}:', end='')
            for i, j in itertools.combinations(self.problem.players, 2):

                if self.x[i, j, r].X > 0.5:
                    print(f' {i+1:>2}-{j+1:<2}', end='')
                elif self.x[j, i, r].X > 0.5:
                    print(f' {j+1:>2}-{i+1:<2}', end='')

            print()

    def print_schedule_crosstable(self):
        print("========= Crosstable =========")
        print('    ' + ' '.join(f'{j+1:^3}' for j in self.problem.players))
        for i in self.problem.players:
            print(f'{i+1:>2}:', end='')
            for j in self.problem.players:
                if i == j:
                    print(f' ---', end='')
                else:
                    ha = 'ᴴ' if sum(self.x[i, j, r].X for r in self.problem.rounds) > 0.5 else 'ᴬ'
                    print(f' {next(r + 1 for r in self.problem.rounds if self.x[i, j, r].X + self.x[j, i, r].X > 0.5):>2}{ha}', end='')

            print()

    def print_schedule_patterns(self):
        print("========= HAP assignment =========")
        for pattern in self.problem.break_patterns:
            r, ha = pattern
            if ha != 'H':
                continue

            print(f'{ha} {r+1:>2}: ', end='')

            for i, letter in enumerate(self.problem.pattern(pattern)):
                print(f'{"-" if i == r else " "}{letter}', end='')

            team = next(i + 1 for i in self.problem.players if (i, pattern) in self.b and self.b[i, pattern].X > 0.5)
            print(f' -> {team:>2}')

        for pattern in self.problem.break_patterns:
            r, ha = pattern
            if ha != 'A':
                continue

            print(f'{ha} {r+1:>2}: ', end='')

            for i, letter in enumerate(self.problem.pattern(pattern)):
                print(f'{"-" if i == r else " "}{letter}', end='')

            team = next(i + 1 for i in self.problem.players if (i, pattern) in self.b and self.b[i, pattern].X > 0.5)
            print(f' -> {team:>2}')

    def print_ranking_haps(self):
        print("========= Ranking HAPs =========")
        f_values = 0.0

        for i in self.problem.players:
            ranking_hap = ''
            print(f'{i+1:>2}:', end='')
            for j in self.problem.opponents(i):
                if sum(self.x[i, j, r].X for r in self.problem.rounds) > 0.5:
                    print(' H', end='')
                    ranking_hap += 'H'
                else:
                    print(' A', end='')
                    ranking_hap += 'A'

            fval = RankingHap(ranking_hap).f_value()
            f_values += fval
            print(f' -> {fval}')

        print(f'F-value: {f_values / self.problem.n}')


if __name__ == '__main__':
    # All single-break feasible d-sequences for n=6,10,14
    d_sequences = {
        6: [
            '221',
        ],
        10: [
            '22221',
            '31221',
        ],
        14: [
            '2222221',
            '1222123',
            '1222213',
            '1213213',
            '3131221',
        ],
    }

    # For n=14, all ranking-HAP sets that have smaller F-value than the optimal one.
    ranking_haps = [
        [
            'AAHAHAHAHAHAH',
            'HHAHAHAHAHAHA',
            'HAHAHAHAHAHAH',
            'AHAHAHAHAHAHA',
            'HAHAHAHAHAHAH',
            'AHAHAHAHAHAHA',
            'HAHAHAHAHAHAH',
            'AHAHAHAHAHAHA',
            'HAHAHAHAHAHAH',
            'AHAHAHAHAHAHA',
            'HAHAHAHAHAHAH',
            'AHAHAHAHAHAHA',
            'HAHAHAHAHAHAH',
            'AHAHAHAHAHAHA',
        ],
        [
            'AHAHAHAHAHAHA',
            'HAHAHAHAHAHAH',
            'AHAHAHAHAHAHA',
            'HAHAHAHAHAHAH',
            'AHAHAHAHAHAHA',
            'HAHAHAHAHAHAH',
            'AHAHAHAHAHAHA',
            'HAHAHAHAHAHAH',
            'AHAHAHAHAHAHA',
            'HAHAHAHAHAHAH',
            'AHAHAHAHAHAHA',
            'HAHAHAHAHAHAH',
            'AHAHAHAHAHAHH',
            'HAHAHAHAHAHAA',
        ],
        [
            'HAHAHAHAHAHAA',
            'AHAHAHAHAHAHA',
            'HAHAHAHAHAHAH',
            'AHAHAHAHAHAHA',
            'HAHAHAHAHAHAH',
            'AHAHAHAHAHAHA',
            'HAHAHAHAHAHAH',
            'AHAHAHAHAHAHA',
            'HAHAHAHAHAHAH',
            'AHAHAHAHAHAHA',
            'HAHAHAHAHAHAH',
            'AHAHAHAHAHAHA',
            'HAHAHAHAHAHAH',
            'HHAHAHAHAHAHA',
        ],
    ]

    # To verify, do not supply a ranking hap set for n=6,10
    # For n=14, verify that the all combinations of d-sequence and ranking hap set yield an infeasible model.
    n = 14
    pattern_index = 4
    ranking_hap_index = 2
    bandwidth = False

    d_sequence = tuple(int(d) for d in d_sequences[n][pattern_index])

    problem = FairSrrProblem(n, break_gaps=d_sequence)

    print(f'n = {n}')
    print(f'd_sequence = {"".join(str(d) for d in d_sequence)}')
    print(f'rHAP index = {ranking_hap_index}')
    print(f'bandwidth = {bandwidth}')

    model = MinRankingFairnessModel(problem, ranking_haps[ranking_hap_index], bandwidth=bandwidth)
    model.model.update()

    model.optimize()

    model.print_schedule_rounds()
    print()
    model.print_schedule_crosstable()
    print()
    model.print_schedule_patterns()
    print()
    model.print_ranking_haps()
    print()

    for v in model.model.getVars():
        if v.X > 0.0:
            print(f'{v.varName} = {v.X}')
