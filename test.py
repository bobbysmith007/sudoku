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

@pytest.fixture
def niceloop_puzzle1_sol():
    p = """
594876123
823914756
617235894
965421378
781653942
342798561
159342687
436587219
278169435
"""
    return sudoku.read_puzzle(p)

# very hard, high branching
@pytest.fixture
def niceloop_puzzle1(niceloop_puzzle1_sol):
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
    P = sudoku.read_puzzle(p)
    P.solution = niceloop_puzzle1_sol
    return P


@pytest.fixture
def niceloop_puzzle2_sol():
    p = """
|384|562|719|
|659|137|248|
|271|498|563|
-------------
|145|286|397|
|893|754|621|
|726|913|854|
-------------
|918|325|476|
|432|671|985|
|567|849|132|
"""
    return sudoku.read_puzzle(p)


# very hard high branching
@pytest.fixture
def niceloop_puzzle2(niceloop_puzzle2_sol):
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
    P = sudoku.read_puzzle(p)
    P.solution = niceloop_puzzle2_sol
    return P


@pytest.fixture
def niceloop_puzzle3_sol():
    p = """
|145|327|698|
|839|654|127|
|672|918|543|
-------------------------------
|496|185|372|
|218|473|956|
|753|296|481|
-------------------------------
|367|542|819|
|984|761|235|
|521|839|764|
"""
    return sudoku.read_puzzle(p)


@pytest.fixture
def niceloop_puzzle3(niceloop_puzzle3_sol):
    p ="""
. . 5 |3 . . |. . .
8 . . |. . . |. 2 .
. 7 . |. 1 . |5 . .
------+------+------
4 . . |. . 5 |3 . .
. 1 . |. 7 . |. . 6
. . 3 |2 . . |. 8 .
------+------+------
. 6 . |5 . . |. . 9
. . 4 |. . . |. 3 .
. . . |. . 9 |7 . .
"""
    P = sudoku.read_puzzle(p)
    P.solution = niceloop_puzzle3_sol
    return P

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
    # print niceloop_puzzle0.solve()
    #print niceloop_puzzle1.solve()
    #print niceloop_puzzle2.solve()
    print niceloop_puzzle3.solve()
