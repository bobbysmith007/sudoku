import sudoku
import pytest

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


@pytest.fixture
def niceloop_discon1():
    p = """
6.7.52.4..
54..6..7.
.2.497.5.
.7524...1
..41895.7
8....5.4.
48...2.95
75..1...4
..6.547.8
"""
    P = sudoku.read_puzzle(p)
    return P
