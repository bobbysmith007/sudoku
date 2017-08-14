from StringIO import StringIO
from copy import deepcopy

PVALS = set(range(1, 10))
PIDXS = set(range(0, 9))


class Index (object):
    def __init__(self, row, col):
        self.row, self.col = row, col

    def id(self):
        return self.row*100+self.col

    def __eq__(self, other):
        return self.row == other.row and self.col == other.col

    def __str__(self):
        return "<%s,%s>" % (self.row, self.col)

    def __repr__(self):
        return "<%s,%s>" % (self.row, self.col)

    def __hash__(self):
        return self.id()

    def __cmp__(self, other):
        # so we can sort
        return self.id().__cmp__(other.id())

    def __iter__(self):
        yield self.row
        yield self.col


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
            return setattr(self, k, getattr(self,k,0)+v)

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


class Link(object):
    def __init__(self, puzzle, from_idx, to_idx, value,
                 strong=False, possibilities=[]):
        for k, v in locals():
            setattr(self, k, v)
        self.idxs = set([self.from_idx, self.to_idx])

    def same_indexes(self, other):
        return other.idxs == self.idxs

    def __eq__(self, other):
        #every strong link is a weak link
        return self.same_indexes(other) and self.value == other.value


class Chain(object):
    def __init__(self, links=[]):
        self.links = links

    def push(self, link):
        self.links.push(link)

    def __iter__(self):
        for l in self.links:
            yield l


class NiceLoop(Chain):
    #  http://www.paulspages.co.uk/sudokuxp/howtosolve/niceloops.htm
    def __init__(self, puzzle, links=[]):
        if links[-1].to_idx != links[0].from_idx:
            raise Exception('Invalid NiceLoop')
        super(Chain, links)