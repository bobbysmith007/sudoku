import pytest, re
import sudoku
import constraints
import models
from models import Index
from test_fixtures import *


def test_strong_links_cols(niceloop_puzzle0):
    p = niceloop_puzzle0
    from_idx = Index(row=3,col=6)
    cols = set(constraints.col_strong_links(p, from_idx))
    assert "[R3C6]=6=[R6C6]" in [str(i) for i in cols]


def test_strong_links_rows(niceloop_puzzle0):
    p = niceloop_puzzle0
    from_idx = Index(row=0,col=4)
    rows = set(constraints.row_strong_links(p, from_idx))
    assert "[R0C4]=8=[R0C8]" in [str(i) for i in rows]

#def test_nice_loop(niceloop_puzzle0):
#    p = niceloop_puzzle0
#    print "Finding loops"
#    for idx in p.free_idxs():
#        for loop in constraints.nice_loops_starting_at(p, idx):
#            print "Loop at: ", loop


def test_solve(niceloop_puzzle0, niceloop_puzzle1, niceloop_puzzle2,
               niceloop_puzzle3):
    pass
    # print niceloop_puzzle0.solve()
    # print niceloop_puzzle1.solve()
    # print niceloop_puzzle2.solve()
    # print niceloop_puzzle3.solve()


# http://sudopedia.enjoysudoku.com/Nice_Loop.html numer 1
def test_nl_discontinuity1(niceloop_discon1):
    p = niceloop_discon1
    find = "[R0C1]-1-[R2C0]=1=[R8C0]=2=[R8C7]=1=[R0C7]-1-[R0C1]"
    found = False
    idx = Index(0, 1)
    for i in constraints.nice_loops_starting_at(p, idx):
        if str(i) == find:
            found = i
            break
    assert found
    pos = p.get_possibilities(idx)
    before = p.make_clone()
    assert constraints.nice_loop_constrainer(p, found)
    assert set([1, 3, 9]) == pos
    afterpos = p.get_possibilities(idx)
    assert 1 not in afterpos
    idxs = set(models.puzzle_range) - set([idx])
    for i in idxs:
        assert before.get_possibilities(i) == p.get_possibilities(i)


def loop_matcher(needle, hay):
    it = re.escape(needle).replace('\\-', '[=-]')
    needle = re.compile(it, re.I)
    return needle.search(hay)

def test_loop_matcher():
    find = "[R0C0]=5=[R0C4]-5-[R5C4]-9-[R5C2]-6-[R1C2]-7-[R0C0]"
    found = "[R0C0]=5=[R0C4]=5=[R5C4]-9-[R5C2]=6=[R1C2]-7-[R0C0]"
    assert loop_matcher(find, found)


# http://sudopedia.enjoysudoku.com/Nice_Loop.html number 2
def test_nl_discontinuity3(niceloop_discon3):
    p = niceloop_discon3
    find = "[R0C0]=5=[R0C4]-5-[R5C4]-9-[R5C2]-6-[R1C2]-7-[R0C0]"
    found = False
    idx = Index(0, 0)
    for i in constraints.nice_loops_starting_at(p, idx):
        if loop_matcher(find, str(i)):
            found = i
            break
    assert found
    print found
    pos = p.get_possibilities(idx)
    before = p.make_clone()
    assert constraints.nice_loop_constrainer(p, found)
    assert set([5, 6, 7]) == pos
    afterpos = p.get_possibilities(idx)
    assert 7 not in afterpos
    idxs = set(models.puzzle_range) - set([idx])
    for i in idxs:
        assert before.get_possibilities(i) == p.get_possibilities(i),\
            "%s %s %s" % (i, p, p.index_solved(i))


# http://sudopedia.enjoysudoku.com/Nice_Loop.html #3
def test_nl_discontinuity2(niceloop_discon2):
    p = niceloop_discon2
    find = "[r3c1]=8=[r5c1]=6=[r5c7]-6-[r4c7]-2-[r4c4]=2=[r3c4]=8=[r3c1]"
    found = False
    idx = Index(3, 1)
    for i in constraints.nice_loops_starting_at(p, idx):
        assert len(i) < 8, "%s" % p
        if loop_matcher(find, str(i)):
            found = i
            break
    assert found
    print found
    pos = p.get_possibilities(idx)
    before = p.make_clone()
    assert constraints.nice_loop_constrainer(p, found)
    assert set([3, 5, 8, 9]) == pos
    afterpos = p.get_possibilities(idx)
    ans = set([8])
    assert ans == afterpos
    idxs = set(models.puzzle_range) - set([idx])
    for i in idxs:
        assert before.get_possibilities(i) == p.get_possibilities(i) or \
            before.get_possibilities(i)-ans == p.get_possibilities(i),\
            "%s %s %s" % (i, p, p.index_solved(i))
