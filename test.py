import pytest
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


def test_find_niceloop(niceloop_discon1):
    p = niceloop_discon1
    find = "[R0C1]-1-[R2C0]=1=[R8C0]=2=[R8C7]=1=[R0C7]-1-[R0C1]"
    found = False
    for i in constraints.nice_loops_starting_at(p, Index(0, 1)):
        print i
        if str(i) == find:
            found = i
            break
    assert found
