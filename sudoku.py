from StringIO import StringIO
import re, traceback, types
import cProfile, pstats, time
import logging
from copy import deepcopy, copy
import puzzles, puzzles2
import models
from models import PVALS, PIDXS, Index, puzzle_range, square_idxs, square
import constraints, traceback

log = logging.getLogger('sudoku')
logging.basicConfig(level=logging.DEBUG)


def tryint(v):
    try:
        return int(v)
    except:
        return None


class SudokuPuzzle (object):
    def __init__(self, puzzle, parent=None, depth=1,
                 start=None, unsolved_idxs=None, possibility_hash=None,
                 stats=None, solution=None, stepByStep=False):
        self.stats = stats or models.Stats(puzzle_branches=1,
                                           constraint_steps=0)
        self.puzzle = puzzle
        self.parent = parent
        self.depth = depth
        self.unsolved_idxs = unsolved_idxs
        self.start = start or time.time()
        self.possibility_hash = possibility_hash or self.init_pos_hash()
        self.solution = solution
        self._current_constraint = None
        self.stepByStep = stepByStep

    def check_solution(self):
        if not self.solution:
            return False
        for i in PIDXS:
            for j in PIDXS:
                idx = Index(i, j)
                pos = self.get_possibilities(idx)
                sol = self.solution.index_solved(idx)
                if sol not in pos:
                    raise Exception("Last constraint step an error at %s %s\n%s",
                                    idx, self._current_constraint, self.print_help())
        return True

    def init_pos_hash(self):
        self.possibility_hash = {}
        self.unsolved_idxs = set([])

        def _get_pos(idx):
            knowns = set()
            for i in PIDXS:
                knowns.add(self.puzzle[i][idx.col])
            for i in PIDXS:
                knowns.add(self.puzzle[idx.row][i])
            for i, j in square(idx):
                knowns.add(self.puzzle[i][j])
            knowns.remove(None)  # avoids many ifs
            return PVALS - knowns

        for idx in puzzle_range:
            v = self.index_solved(idx)
            if v:
                pos = set([v])
            else:
                pos = _get_pos(idx)
                self.unsolved_idxs.add(idx)
            self.possibility_hash[idx] = pos
        return self.possibility_hash

    def make_clone(self):
        c = SudokuPuzzle(
            deepcopy(self.puzzle), self, self.depth, self.start,
            deepcopy(self.unsolved_idxs),
            deepcopy(self.possibility_hash),
            self.stats)
        return c
        
    def make_child(self, box=None, new_val=None):
        self.stats.puzzle_branches += 1
        idx = self.stats.puzzle_branches
        if idx % 1000 == 0:
            print "Making branch (idx:%d, depth:%d): %s val:%s - %ss" % \
                (idx, self.depth, box, new_val, time.time()-self.start)
        c = SudokuPuzzle(
            deepcopy(self.puzzle), self, self.depth+1, self.start,
            deepcopy(self.unsolved_idxs),
            deepcopy(self.possibility_hash),
            self.stats)
        if box and new_val:
            c.set_index_possibilities(box.idx, set([new_val]))
        return c

    def open_boxes(self):
        return sorted([models.Box(idx, self.get_possibilities(idx))
                       for idx in puzzle_range
                       if not self.index_solved(idx)],
                      key=len)

    def search(self):
        try:
            self.constrain()
        except models.NoPossibleValues, e:
            if self.parent:
                raise e
            else:
                print "ERROR ON BOARD:\n", self.print_help(), "\n\n", self
                raise e
        if self.is_solved(): return self

        logging.debug("Couldn't solve board via constraints, %s\n"
                      "%s\nStarting to guess", self, self.print_help())
        # really only care about the first open box as it WILL be one
        # of the values there if our model is correct up till now
        # otherwise any mistake is enough to backtrack
        box = self.open_boxes()[0]
        children = []
        for v in box.val or []:
            try:
                c = self.make_child(box, v)
                children.append(c)
                sol = c.search()
                if sol:
                    return sol
            except models.NoPossibleValues:
                pass

    def solve(self):
        sol = self.search()
        if sol and sol.is_solved():
            #self.puzzle = deepcopy(sol.puzzle)
            sol.status()
        else:
            print self.print_help(), "\n\n",self
            raise Exception("Puzzle Not Solved...")
        return sol

    def index_solved(self, idx):
        return self.puzzle[idx.row][idx.col]

    def constrain(self):

        # Only resort to a higher reasoning 
        # when a lesser reasoning system fails us
        #
        # This should allow us to determine when 
        # a reasoning system is completely subsumed
        # by a more general one (xy_wing vs xy_chain)
        def do():
            self.stats.inc('constraint_steps')
            self._solved_this_cycle = False
            self._constrained_this_cycle = False
            if self.stepByStep:
                log.info('Constrainer Step: %d\n %s\n ---- \n',
                         self.stats.get('constraint_steps'),
                         self.print_help())
            for con in constraints.constraintsToRun:
                self._current_constraint = con
                con(self)
                if self._constrained_this_cycle or self._solved_this_cycle:
                    return True
        while(do()):
            pass

    def free_idxs(self):
        return (idx
                for i in PIDXS
                for j in PIDXS
                for idx in [Index(i, j)]
                if not self.index_solved(idx))

    def bi_value_idxs(self):
        return (idx
                for idx in self.free_idxs
                if len(self.get_possibilities(idx)) == 2)

    def free_in_row(self, idx_in):
        return set([idx
                    for j in PIDXS
                    for idx in [Index(idx_in.row, j)]
                    if not self.index_solved(idx)])

    def free_in_col(self, idx_in):
        return set([idx
                    for i in PIDXS
                    for idx in [Index(i, idx_in.col)]
                    if not self.index_solved(idx)])

    def free_in_square(self, idx_in):
        return set([idx
                    for idx in square(idx_in)
                    if not self.index_solved(idx)])

    def free_related_cells(self, idx):
        return (self.free_in_row(idx) |
                self.free_in_col(idx) | self.free_in_square(idx)) - set([idx])

    def free_related_possibilities(self, idx):
        idxs = self.free_related_cells(idx)-set(idx)
        return self.get_possibilities(*idxs)

    def closed_square_row(self, idx):
        return [i for i in square_idxs(idx.row)
                if self.index_solved(Index(i, idx.col))]

    def closed_square_col(self, idx):
        return [j for j in square_idxs(idx.col)
                if self.index_solved(Index(idx.row, j))]

    def is_in_row(self, val, row):
        for j in PIDXS:
            if self.puzzle[row][j] == val:
                return True

    def is_in_col(self, val, col):
        for i in PIDXS:
            if self.puzzle[i][col] == val:
                return True
            
    def set_index_possibilities(self, idx, pos):
        constrained_this_set = False
        if not isinstance(pos, set):
            pos = set([pos])
        old = self.possibility_hash.get(idx, set())
        if len(pos) == 0:
            print "Failed to set %s to %s from %s" % \
                (idx, pos, self._current_constraint)
            raise models.NoPossibleValues(idx)
        self.possibility_hash[idx] = pos
        if len(pos) == 1 and not self.index_solved(idx):
            if self.stepByStep:
                log.info('Solved %s for %s', idx, pos)
            self._solved_this_cycle = True
            self.puzzle[idx.row][idx.col] = list(pos)[0]
            if idx in self.unsolved_idxs:
                self.unsolved_idxs.remove(idx)
            for i in self.free_related_cells(idx):
                if i == idx:
                    continue
                self.remove_index_possibilities(i, pos)
        if old != pos:
            self._constrained_this_cycle = True
            constrained_this_set = True
            self.check_solution()
        return constrained_this_set

    def remove_index_possibilities(self, idx, pos):
        if not isinstance(pos, set):
            pos = set([pos])
        old = self.get_possibilities(idx)
        new_pos = old-pos
        if self.stepByStep:
            log.info('Removed Possibilities %s from %s leaving %s',
                     pos, idx, new_pos)
        return self.set_index_possibilities(idx, new_pos)

    def get_possibilities(self, *idxs):
        if len(idxs) == 0:
            return set()
        sets = [self.possibility_hash.get(i) for i in idxs]
        return set.union(*sets) or set()

    def is_solved(self):
        for i in puzzle_range:
            if not self.index_solved(i):
                return False
        return self

    def status(self):
        s = StringIO()
        if self.is_solved():
            s.write('Solved Puzzle: \n')
        else:
            s.write('Unsolved Puzzle:\n')
        s.write(str(self.stats))
        return s.getvalue()

    def __str__(self):
        s = StringIO()
        s.write("-------------------------------\n")
        s.write(self.status())
        s.write("-------------------------------\n")
        for i in PIDXS:
            s.write('|')
            for j in PIDXS:
                s.write(' ')
                if self.index_solved(Index(i, j)):
                    s.write(self.puzzle[i][j])
                else:
                    s.write('.')
                s.write(' ')
                if j % 3 == 2:
                    s.write('|')
            s.write('\n')
            if i % 3 == 2:
                s.write("-------------------------------\n")
        return s.getvalue()

    def print_help(self):
        lb = "-------------------------------"\
            "---------------------------------"\
            "-------------------------------\n"
        s = StringIO()
        s.write(lb)
        s.write(self.status())
        s.write(lb)
        for i in PIDXS:
            s.write('||')
            for j in PIDXS:
                idx = models.Index(i, j)
                pos = self.get_possibilities(idx)
                for l in PVALS:
                    if l in pos:
                        s.write(l)
                    else:
                        s.write(' ')
                s.write('|')
                if j % 3 == 2:
                    s.write('|')
            s.write('\n')
            if i % 3 == 2:
                s.write(lb)
        return s.getvalue()


def read_puzzle(s):

    # skip first/last line
    s = re.sub(r'\n\n+', '\n', re.sub(r'-|\+|\|| |,', "", s))
    partial_sol = [i for i in s.splitlines() if i.strip()]
    
    def get(i, j):
        if len(partial_sol) > i and len(partial_sol[i]) > j:
            return tryint(partial_sol[i][j])
    puzzle = SudokuPuzzle([[get(i, j) for j in PIDXS] for i in PIDXS])
    # print puzzle
    return puzzle


PUZZLE = read_puzzle(puzzles.puzzles[0])


def solve_puzzle(s):
    global PUZZLE
    if isinstance(s, str):
        s = read_puzzle(s)
    PUZZLE = s
    p = s.solve()
    assert p.is_solved()
    PUZZLE = p
    return p


def solve_some_puzzles():
    i = 1
    total_time = 0
    puz = puzzles.puzzles  # [5:]
    stats = models.Stats()
    for p in puz:
        print "Starting puzzle %s" % i
        p = read_puzzle(p)
        p.start = time.time()
        s = solve_puzzle(p)
        stats.inc(s.stats)
        print s
        ptime = time.time()-p.start
        total_time += ptime
        print "Done with puzzle %s in %s sec" % (i, ptime)
        i += 1
    print "\n -- TOTALS -- \nDone with %d puzzles in %s sec:\n%s" % \
        (len(puz), total_time, stats)

     
if __name__ == "__main__":
    solve_some_puzzles()
else:
    try:
        pf = 'sudoku.v4'
        # cProfile.run('sudoku.solve_some_puzzles()', pf)
        # p = pstats.Stats(pf)
        # p.strip_dirs().sort_stats(-1)
        # p.sort_stats('time').print_stats(10)
    except NameError, e:
        print "Reload module to run profiling"
        traceback.print_exc();
    except Exception, e:
        traceback.print_exc();
