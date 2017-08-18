import logging
from StringIO import StringIO
from copy import deepcopy

PVALS = set(range(1, 10))
PIDXS = set(range(0, 9))

log = logging.getLogger('sudoku')


class Index (object):
    def __init__(self, row, col):
        self.row, self.col = row, col

    def id(self):
        return self.row*100+self.col

    def __eq__(self, other):
        return self.row == other.row and self.col == other.col

    def __str__(self):
        return "[R%sC%s]" % (self.row, self.col)

    def __repr__(self):
        return "Index(%s,%s)" % (self.row, self.col)

    def __hash__(self):
        return self.id()

    def __cmp__(self, other):
        # so we can sort
        return self.id().__cmp__(other.id())

    def __iter__(self):
        yield self.row
        yield self.col

    def same_square(self, idx):
        ridx = square_idxs(self.row)
        if idx.row not in ridx:
            return False
        cidx = square_idxs(self.col)
        if idx.col not in cidx:
            return False
        return True


def square_idxs(i):
    r = i / 3
    return range(r*3, r*3+3)


def square(idx):
    return cross(square_idxs(idx.row), square_idxs(idx.col))


def share_a_row(*idxs):
    return all(idx.row == idxs[0].row
               for idx in idxs[1:])


def share_a_col(*idxs):
    return all(idx.col==idxs[0].col
               for idx in idxs[1:])


def share_a_square(*idxs):
    return all(idx.col/3==idxs[0].col/3 and idx.row/3==idxs[0].row/3
               for idx in idxs[1:])

def cross(l1, l2):
    return [Index(i, j)
            for i in l1
            for j in l2]


puzzle_range = cross(PIDXS, PIDXS)


class PosCount(object):
    def __init__(self, val=None, idxs=None):
        self.val, self.idxs = val, idxs or []

    def __len__(self):
        return len(self.idxs)

    def __repr__(self):
        return "|%d|" % len(self)

    def __str__(self):
        return "|%d|" % len(self)

    def __iter__(self):
        return iter(self.idxs)


class Box (object):
    def __init__(self, idx, val):
        self.idx,self.val = idx,val
    def __len__(self):
        if isinstance(self.val,int): return 1
        elif not self.val: return 0
        return len(self.val)
    def __str__(self):
        return "Box(%s,%s)"%(self.idx,self.val)


class Ref (object):
    def __init__(self,**kws):
        for k,v in kws.items():
            setattr(self, k, v)


class Stats (object):
    def __init__(self,**kws):
        for k,v in kws.items():
            setattr(self, k, v)

    def inc(self,k,v=1):
        if isinstance(k, Stats):
            for k,v in vars(k).items():
                self.inc(k,v)
        else:
            val = getattr(self,k,0)+v
            setattr(self, k, val)
            log.debug('Stats %s : %s', k, v)
            return val

    def get(self, k):
        return getattr(self, k, 0)

    def __str__ (self):
        s = StringIO()
        stats = deepcopy(vars(self))
        del stats['constraint_steps']
        del stats['puzzle_branches']
        s.write("  %s - Constraint Cycles\n" % self.constraint_steps)
        s.write("  %s - Branches\n\n" % self.puzzle_branches)
        items = stats.items()
        items.sort()
        for k,v in items:
            s.write('  %s : %s \n' % (k,v))
        return s.getvalue()


class ConstrainedThisCycle(Exception):
    pass


class NoPossibleValues(Exception):
    def __init__(self, idx=None, data=None):
        self.idx,self.data = idx,data

    def __str__(self):
        return "NoPossibleValues for %s:%r" % (self.idx, self.data)


def is_square_strong_link(puzzle, from_idx, to_idx, v):
    if not from_idx.same_square(to_idx):
        return False
    other_idx = puzzle.free_in_square(from_idx) - set([from_idx, to_idx])
    other_pos = puzzle.get_possibilities(*other_idx)
    if v not in other_pos:
        return True


def is_col_strong_link(puzzle, from_idx, to_idx, v):
    if from_idx.col != to_idx.col:
        return False
    other_idx = puzzle.free_in_col(from_idx) - set([from_idx, to_idx])
    other_pos = puzzle.get_possibilities(*other_idx)

    if v not in other_pos:
        return True


def is_row_strong_link(puzzle, from_idx, to_idx, v):
    if from_idx.row != to_idx.row:
        return False
    other_idx = puzzle.free_in_row(from_idx) - set([from_idx, to_idx])
    other_pos = puzzle.get_possibilities(*other_idx)
    if v not in other_pos:
        return True


class Link(object):
    def __init__(self, puzzle, from_idx, to_idx, value,
                 strong=False, possibilities=[]):
        for k, v in locals().items():
            setattr(self, k, v)
        self.idxs = set([self.from_idx, self.to_idx])
        if not strong:
            self._calc_strong()

    def same_indexes(self, other):
        return other.idxs == self.idxs

    def __eq__(self, other):
        #every strong link is a weak link
        return self.same_indexes(other) and self.value == other.value

    def __str__(self):
        delim = '-'
        if self.strong:
            delim = '='
        return "%s%s%d%s%s" % (
            self.from_idx, delim, self.value, delim, self.to_idx)

    def __repr__(self):
        return str(self)

    def _calc_strong(self):
        if is_square_strong_link(
                self.puzzle, self.from_idx, self.to_idx, self.value) \
           or is_row_strong_link(
               self.puzzle, self.from_idx, self.to_idx, self.value) \
           or is_col_strong_link(
               self.puzzle, self.from_idx, self.to_idx, self.value):
            self.strong = True
            return True



class Chain(object):
    def __init__(self, puzzle, links=[]):
        self.puzzle = puzzle
        self.links = links

    def push(self, link):
        self.links.push(link)

    def __iter__(self):
        for l in self.links:
            yield l

    def __str__(self):
        out = str(self.links[0])
        for l in self.links[1:]:
            out += str(l)[6:]
        return out

    def __len__(self):
        return len(self.links)

def nl_2strong(p, l0, l1):
    ans = l0.strong and l1.strong and l0.value != l1.value
    #if ans: log.debug("2strong, l1:%s", l1)
    return ans


def nl_2weak(p, l0, l1):
    ans = not l0.strong and not l1.strong and \
          l0.value != l1.value and len(p.get_possibilities(l1.from_idx)) == 2
    #if ans: log.debug("2weak, l1:%s , l1.pos:%s", l1.from_idx, l1.possibilities)
    return ans


def nl_weakstrong(p, l0, l1):
    ans = l0.strong != l1.strong and l0.value == l1.value
    #if ans: log.debug("weakstrong, %s %s", l0, l1)
    return ans


class NiceLoop(Chain):
    #  http://www.paulspages.co.uk/sudokuxp/howtosolve/niceloops.htm
    def __init__(self, puzzle, links=[]):
        super(NiceLoop, self).__init__(puzzle, links)
        if links[-1].to_idx != links[0].from_idx:
            raise Exception('Invalid NiceLoop %s' % (self))
        self.continuous = self.is_continuous()
        # TODO: validate links

    def is_continuous(self):
        i = 0
        l0 = self.links[-1]
        cont = True
        for l1 in self.links[:-1]:
            if (not nl_weakstrong(self.puzzle, l0, l1)
                and not nl_2weak(self.puzzle, l0, l1)
                and not nl_2strong(self.puzzle, l0, l1)):
                cont = False
                if i > 0:
                    raise Exception(
                        "Not a valid niceloop (discontinuity at %s %s, %s)",
                        l0, l1, i)
            l0 = l1
            i += 1
        return cont
