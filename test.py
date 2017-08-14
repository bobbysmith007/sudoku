import pytest
import sudoku
import constraints
import models
from models import Index

@pytest.fixture
def niceloop_puzzle0():
    p = """
...9..4...
..8.1.5..
3....2.6.
..71.9.8.
...4.6...
.1....9..
.2.7.1..3
..5.9.1..
1.6..8...
"""
    return sudoku.read_puzzle(p)


# very hard high branching
@pytest.fixture
def niceloop_puzzle2 ():
    p = """
. . . |. 6 . |. . .
. 5 9 |. . . |. . 8
2 . . |. . 8 |. . .
------+------+------
. 4 5 |. . . |. . .
. . 3 |. . . |. . .
. . 6 |. . 3 |. 5 4
------+------+------
. . . |3 2 5 |. . 6
. . . |. . . |. . .
. . . |. . . |. . .
"""
    return sudoku.read_puzzle(p)


# very hard, high branching
@pytest.fixture
def niceloop_puzzle1():
    p = """
....7..2.
8.......6
.1.2.5...
9.54....8
.........
3....85.1
...3.2.8.
4.......9
.7..6....
"""
    return sudoku.read_puzzle(p)

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


def test_solve(niceloop_puzzle0, niceloop_puzzle1, niceloop_puzzle2):
    # print niceloop_puzzle0.solve()
    print niceloop_puzzle1.solve()
    print niceloop_puzzle2.solve()
