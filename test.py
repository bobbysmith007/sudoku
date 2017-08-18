import pytest, re
import sudoku
import constraints
import models
from models import Index
from test_fixtures import *


def sol(p):
    try:
        print p.solve()
    except Exception, e:
        print e
        assert False, "Shouldnt get an error %s" % e


def test_solve0(niceloop_puzzle0):
    sol(niceloop_puzzle0)


def test_solve1(niceloop_puzzle1):
     sol(niceloop_puzzle1)


def test_solve2(niceloop_puzzle2):
    sol(niceloop_puzzle2)


def test_solve3(niceloop_puzzle3):
    sol(niceloop_puzzle3)


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
    assert constraints.nice_loop_constrainer_discont(p, found)
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
    assert constraints.nice_loop_constrainer_discont(p, found)
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
    assert constraints.nice_loop_constrainer_discont(p, found)
    assert set([3, 5, 8, 9]) == pos
    afterpos = p.get_possibilities(idx)
    ans = set([8])
    assert ans == afterpos, "%s" % p
    idxs = set(models.puzzle_range) - set([idx])
    for i in idxs:
        assert before.get_possibilities(i) == p.get_possibilities(i) or \
            before.get_possibilities(i)-ans == p.get_possibilities(i),\
            "%s %s %s" % (i, p, p.index_solved(i))

# http://sudopedia.enjoysudoku.com/Nice_Loop.html #4
def test_nl_cont1(niceloop_cont1):
    p = niceloop_cont1
    find = "[r0c4]=4=[r8c4]=7=[r8c8]-7-[r2c8]-4-[r2c1]=4=[r0c0]-4-[r0c4]"
    found = False
    idx = Index(0, 4)
    for i in constraints.nice_loops_starting_at(p, idx):
        assert len(i) < 8, "%s" % p.print_help()
        if loop_matcher(find, str(i)):
            found = i
            break
    assert found
    print found
    before = p.make_clone()
    assert constraints.nice_loop_constrainer_cont(p, found)
    assert set([2, 4, 5, 7]) == before.get_possibilities(Index(1, 8))
    assert 7 not in p.get_possibilities(Index(1, 8))
    assert 4 not in p.get_possibilities(Index(2, 3))
    assert set([4, 7]) == p.get_possibilities(Index(8, 4))

    idxs = set(models.puzzle_range) - \
           set([Index(1, 8), Index(2, 3), Index(8, 4)])
    for i in idxs:
        assert before.get_possibilities(i) == p.get_possibilities(i), \
            "%s %s %s" % (i, p, p.index_solved(i))



#http://www.paulspages.co.uk/sudokuxp/howtosolve/niceloops.htm
def test_nl_sf_replace(niceloop_puzzle4_1):
    p = niceloop_puzzle4_1
    find = "[R0C3]=7=[R1C4]=6=[R6C4]=4=[R6C3]-4-[R0C3]"
    found = False
    idx = Index(0, 3)
    for i in constraints.nice_loops_starting_at(p, idx):
        assert len(i) < 8, "%s" % p.print_help()
        if loop_matcher(find, str(i)):
            found = i
            break
    assert found
    print found
    before = p.make_clone()

    assert constraints.nice_loop_constrainer_discont(p, found)
    assert 4 in before.get_possibilities(idx)
    assert 4 not in p.get_possibilities(idx)
    idxs = set(models.puzzle_range) - set([idx])
    for i in idxs:
        assert before.get_possibilities(i) == p.get_possibilities(i), \
            "%s %s %s" % (i, p, p.index_solved(i))
