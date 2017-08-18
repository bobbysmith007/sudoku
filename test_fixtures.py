import sudoku
import models
from models import Index
import pytest

@pytest.fixture
def niceloop_puzzle0_sol():
    p = """
562987431
748613529
391542768
457139682
289476315
613825947
924761853
835294176
176358294
"""
    return sudoku.read_puzzle(p)

@pytest.fixture
def niceloop_puzzle0(niceloop_puzzle0_sol):
    p = """
...9..4..
..8.1.5..
3....2.6.
..71.9.8.
...4.6...
.1....9..
.2.7.1..3
..5.9.1..
1.6..8...
"""
    P = sudoku.read_puzzle(p)
    P.solution = niceloop_puzzle0_sol
    return P

def niceloop_p0():
    P = niceloop_puzzle0(niceloop_puzzle0_sol())
    P.stepByStep = True
    return P.solve()

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


def niceloop_p1():
    return niceloop_puzzle0(niceloop_puzzle1_sol())


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


##  http://sudopedia.enjoysudoku.com/Nice_Loop.html

@pytest.fixture
def niceloop_discon1():
    p = """
6.752.4..
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

@pytest.fixture
def niceloop_discon2():
    p = """
8.93..2..
.1.2.8..6
2..15..87
...6..4..
7..9.15.8
..24.....
6..84....
5..7..83.
..85.26..
"""
    P = sudoku.read_puzzle(p)
    return P


@pytest.fixture
def niceloop_discon3():
    p = """
.831.2..4
.2..8.3..
491637582
..876.25.
..5.28..7
27....84.
85427..3.
132.4.7.8
.6.813425
"""
    P = sudoku.read_puzzle(p)
    return P


@pytest.fixture
def niceloop_cont1():
    p = """
.738.9.16
8...163..
1.6.5389.
..813.7..
73.6...4.
..1.97638
31796.4..
..45....3
.853...6.
"""
    P = sudoku.read_puzzle(p)
    P.set_index_possibilities(Index(0, 0), set([4, 5]))
    P.set_index_possibilities(Index(0, 4), set([2, 4]))
    P.set_index_possibilities(Index(1, 1), set([5, 9]))
    P.set_index_possibilities(Index(1, 2), set([2, 9]))
    P.set_index_possibilities(Index(1, 3), set([4, 7]))
    P.set_index_possibilities(Index(1, 7), set([2, 5, 7]))
    P.set_index_possibilities(Index(1, 8), set([2, 4, 5, 7]))
    P.set_index_possibilities(Index(2, 1), set([4, 2]))
    P.set_index_possibilities(Index(2, 3), set([2, 4, 7]))
    P.set_index_possibilities(Index(2, 8), set([4, 7]))
    P.set_index_possibilities(Index(7, 4), set([7, 8]))
    P.set_index_possibilities(Index(7, 7), set([2, 7, 8]))
    P.set_index_possibilities(Index(8, 4), set([2, 4, 7]))
    P.set_index_possibilities(Index(8, 8), set([1, 2, 7, 9]))
    return P


@pytest.fixture
def niceloop_puzzle4():
    p = """
..9.2.3..
..21..9.8
..68....1
..361..9.
.9.....8.
.5..391..
3....78..
4.7..16..
..8.5.4..
"""
    P = sudoku.read_puzzle(p)
    return P


@pytest.fixture
def niceloop_puzzle4_1():
    p = """
189.2.3..
..21..9.8
..689...1
273618594
691....83
854.391..
3.5..78..
427.816..
9.8.5.4..
"""
    P = sudoku.read_puzzle(p)
    return P
