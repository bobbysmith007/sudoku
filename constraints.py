import logging
from itertools import combinations, groupby
import models
from models import PVALS, PIDXS, square_idxs, \
    share_a_row, share_a_col, share_a_square


def are_distinct_sets(x, y):
    return len(x & y) == 0


def run_constraints_across_houses(constraint):
    def fn(puzzle):
        for i in range(0, 3):
            for j in range(0, 3):
                idxs = puzzle.free_in_square(models.Index(i*3, j*3))
                constraint(puzzle, idxs, 'square')
                if puzzle._constrained_this_cycle:
                    return True

        for j in PIDXS:
            idxs = puzzle.free_in_col(models.Index(0, j))
            constraint(puzzle, idxs, 'col')
            if puzzle._constrained_this_cycle:
                return True

        for i in PIDXS:
            idxs = puzzle.free_in_row(models.Index(i, 0))
            constraint(puzzle, idxs, 'row')
            if puzzle._constrained_this_cycle:
                return True
    return fn


def single_possibility(puzzle):
    for idx in list(puzzle.unsolved_idxs):
        pos = puzzle.get_possibilities(idx)
        if len(pos) == 1:
            puzzle.stats.inc('single_possibility')
            puzzle.set_index_possibilities(idx, pos)


def xwing_col_constraint(puzzle):
    """
    Implements the XWing strategy looking through cols
    http://www.sudopedia.org/wiki/X-Wing
    """
    # buid a collection of row->possibility->number of times that
    # possibility occurs
    posCounts = [[models.PosCount(v) for v in PVALS]
                 for i in PIDXS]
    for i in list(puzzle.unsolved_idxs):
        for val in puzzle.get_possibilities(i):
            posCounts[i.row][val-1].idxs.append(i)

    gen = ((i1, i2, val)
           for i1 in PIDXS
           for i2 in range(i1+1, len(PIDXS))
           for val in PVALS
           if len(posCounts[i1][val-1])==2 and
              len(posCounts[i2][val-1])==2)

    #two cells that share value values in two rows to make a square
    for i1,i2,val in gen:
        # two rows contain two cells in the
        # same two columns with the same set of two possibilities
        c1,c2 = posCounts[i1][val-1].idxs
        c3,c4 = posCounts[i2][val-1].idxs
        if c1.col>c2.col: c1,c2 = c2,c1
        if c3.col>c4.col: c3,c4 = c4,c3
        if c1.row!=c2.row or c3.row != c4.row or \
                c1.col!=c3.col or c2.col!=c4.col: continue  # not an xwing square
        # not relevant to me
        # if c1.col!=idx.col and c2.col!=idx.col: continue
        #print "XWING ",c1,c2,c3,c4,"\n",puzzle.print_help()
        # we have an xwing square
        sv = set([val])
        others = (set(puzzle.free_in_col(c1))|
                  set(puzzle.free_in_col(c2)))-set([c1,c2,c3,c4])
        for o in others:
            if puzzle.remove_index_possibilities(o,sv):
                puzzle.stats.inc('xwing_col')
                return True

def xwing_row_constraint(puzzle):
    """
    Implements the XWing strategy looking through rows
    http://www.sudopedia.org/wiki/X-Wing
    """
    posCounts = [[models.PosCount(v) for v in PVALS]
                 for i in PIDXS]
    for i in list(puzzle.unsolved_idxs):
        for val in puzzle.get_possibilities(i):
            posCounts[i.col][val-1].idxs.append(i)

    gen = ((j1,j2,val)
           for j1 in PIDXS
           for j2 in range(j1+1,len(PIDXS))
           for val in PVALS
           if len(posCounts[j1][val-1])==2
           and len(posCounts[j2][val-1])==2)

    #two cells that share a value in two cols to make a square
    for j1,j2,val in gen:
        c1,c3 = posCounts[j1][val-1].idxs
        c2,c4 = posCounts[j2][val-1].idxs
        if c1.col>c2.col: c1,c2 = c2,c1
        if c3.col>c4.col: c3,c4 = c4,c3
        if c1.row!=c2.row or c3.row != c4.row or \
                c1.col!=c3.col or c2.col!=c4.col: continue  # not an xwing square
        #if c1.row!=idx.row and c3.row!=idx.row: continue # not relevant to me
        # print "XWING ",c1,c2,c3,c4,"\n",puzzle.print_help()
        # we have an xwing square
        sv = set([val])
        others = ( puzzle.free_in_row(c1) | puzzle.free_in_row(c3)) - \
            set([c1,c2,c3,c4])
        for o in others:
            if puzzle.remove_index_possibilities(o,sv):
                puzzle.stats.inc('xwing_row')
                return True

def squeeze(puzzle):
    """ constrain possibilities by squeezing """
    def val_in_other_rows (v, idx):
        idxs = square_idxs(idx.row)
        idxs.remove(idx.row)
        return puzzle.is_in_row(v, idxs[0]) and puzzle.is_in_row(v,idxs[1])

    def val_in_other_cols (v, idx):
        idxs = square_idxs(idx.col)
        idxs.remove(idx.col)
        return puzzle.is_in_col(v, idxs[0]) and puzzle.is_in_col(v,idxs[1])

    gen = ((v,idx)
           for idx in list(puzzle.unsolved_idxs)
           for v in puzzle.get_possibilities(idx)
           if val_in_other_cols(v, idx)
           and val_in_other_rows(v, idx))

    for v, idx in gen:
        if puzzle.set_index_possibilities(idx, set([v])):
            puzzle.stats.inc('squeeze')
            return True


def unique_possibility(puzzle, cells, name):
    gen = ((v, cell)
           for cell in cells
           for v in puzzle.get_possibilities(cell)
           for others in [(cells - set([cell]))]
           if len(others) > 0
           if v not in puzzle.get_possibilities(*others))
    for v, cell in gen:
        if(puzzle.set_index_possibilities(cell, set([v]))):
            puzzle.stats.inc('unique_possibility_' + name)
            return True


def combo_sets(inp, *lengths):
    if len(lengths) == 0:
        lengths = range(2, len(inp) - 1)
    for i in lengths:
        for v in combinations(inp, i):
            yield set(v)


def set_exclusions(puzzle, free_list, name):
    """
    Handles both naked and hidden sets exclusion
    http://www.sudopedia.org/wiki/Naked_Subset
    http://www.sudopedia.org/wiki/Hidden_Subset

    also handles locked sets though that is a bit irrelevant
    as we would have found them anyway on the next pass

    If a set of cells are the only cells that can hold a
    set of values of equal length, then those values must be
    in those squares. So remove all other possibilities from
    those cells, and remove our values from all the other
    cells in the (col/row/square)
    """
    free_list = set(free_list)
    unused_idxs = models.Ref(it=free_list)
    def handle_set (vals, idxs):
        """ constrain the related indexes in the set """

        others = set()
        # http://www.sudopedia.org/wiki/Locked_Candidates
        # if the set is locked we can add more others to the list:
        an_idx = list(idxs)[0]

        if share_a_square(*idxs):
            others |= puzzle.free_in_square(an_idx)
        if share_a_col(*idxs):
            others |= puzzle.free_in_col(an_idx)
        if share_a_row(*idxs):
            others |= puzzle.free_in_row(an_idx)

        others = others - idxs
        to_inc = False
        for idx in idxs: # our indexes cant have anything but our values
            to_inc |= puzzle.set_index_possibilities(
                idx, vals & puzzle.get_possibilities(idx))
        for idx in others: # other indexes cant have our values
            to_inc |= puzzle.remove_index_possibilities(idx, vals)
        if to_inc:
            puzzle.stats.inc('set_exclusions_'+name)
        return to_inc

    # look for sets by looking at every combination
    # of indexes, and finding ones that share a
    # common subset of equal length of values
    for idxs in combo_sets(unused_idxs.it):
        idxs = set(idxs)
        idx_pos = puzzle.get_possibilities(*idxs)

        #indexes not in the subset we are looking at
        others = (unused_idxs.it - idxs)
        other_pos = puzzle.get_possibilities(*others)

        # every set of possibilities of the correct length should
        # be tested to see if they form a block of numbers that
        # could only be put here
        pos_sets = combo_sets(idx_pos, len(idxs))
        for vals in pos_sets:
            vals = set(vals)
            if are_distinct_sets(vals, other_pos):
                if handle_set(vals,idxs):
                    return True

def naked_set_exclusions(puzzle, free_list, name):
    """
    This is deprecated code (replaced by sets exclusion) that looks for naked sets
    http://www.sudopedia.org/wiki/Naked_Subset
    """
    s = sorted(free_list,key=puzzle.get_possibilities)
    # group free squares by shared possiblity lists
    kfn = lambda x: len(x[0])
    groups = sorted(((i,list(g))
                     for i,g in groupby(s, puzzle.get_possibilities)),
                    key=kfn)

    naked_groups=[]
    not_naked = []
    for i1, gl1 in groups:
        if len(i1) == len(gl1) and len(i1) > 1 :
            naked_groups.append((i1,gl1))
        else:
            not_naked.append((i1,gl1))

    # this section handles the indistinct subset possibilites of multiplesquares
    # ex: [set(1,2),set(2,3),set(1,2,3)] is a naked triple
    def fn():
        ahead = 1
        not_naked.sort(key=kfn)
        for i1,gl1 in not_naked:
            for i2, gl2 in not_naked[ahead:]:
                if i1 <= i2: #subset
                    if len(gl1)+len(gl2) == len(i2):
                        not_naked.remove((i1,gl1))
                        not_naked.remove((i2,gl2))
                        naked_groups.append((i2,gl1+gl2))
                        # puzzle.stats.inc(name+'_complex_constraint')
                        return True
                    else:
                        not_naked.remove((i1,gl1))
                        not_naked.remove((i2,gl2))
                        not_naked.append((i2,gl1+gl2))
                        return True
            ahead +=1
    while(fn()):pass

    # if we know these possiblities are being
    # used up in the naked set, might as well remove them
    # from everyone elses possibilities
    for not_pos,gl in naked_groups:
        for cell in free_list-set(gl):
            if puzzle.remove_index_possibilities(cell,not_pos):
                puzzle.stats.inc('naked_set_exclusions_'+name)


def xy_chain_links(puzzle):
    """
    XY chains are a generalization of the XY-wing strategy
     http://www.sudopedia.org/wiki/XY-Chain
     An XY-wing is a XY-chain len 3

     This implementation (based off golden chains pdf) seems to
     differ from that described on sudopedia, in that my chain is
     all weak links rather than alternating weak/strong links


     Each chain follows these rules:
      1. it is 3 or more cells long
      2. each cell contains two possibilities
      3. each cell is bridged to the next by a value
         that is different from the previous bridge
      4. the chain is complete when we get a cell that shares
         a value with the first that is different from first cells
         bridge value
    """
    free = lambda x:puzzle.free_related_cells(x)
    pos = lambda x:puzzle.get_possibilities(x)
    pos_intersect = lambda x: set.intersection(*map(pos,x))
    head_pos,head_free = None,None
    def rec(chain, bridge=set() ):
        tail = chain[-1]
        tail_pos = pos(tail)
        # if this cell doesnt contain 2 possibilities
        if len(tail_pos) != 2: raise StopIteration()
        if len(chain)>=3: # need three cells for a chain
            #three consecutive links cannot share a single value:
            if len(pos_intersect(chain[-3:])) !=0:
                raise StopIteration()
            # the bridge between consecutive cells must be different
            if pos_intersect(chain[-3:-1]) == pos_intersect(chain[-2:]):
                raise StopIteration()
            chain_val = (head_pos & tail_pos) - bridge
            first_bridge = head_pos & pos(chain[1])
            if len(chain_val)==1 and chain_val != first_bridge:
                yield (chain, chain_val)
                # once a chain ends we are done with that branch, dont keep adding links
                # raise StopIteration()

        for new in free(tail) - set(chain):
            # if new shares a single possibility with tail
            # then it is a new link in the chain
            bridge = pos(new)&tail_pos
            if len(bridge)==1:
            #and new not in head_free:
                for i in rec(chain+[new], bridge):
                    yield i

    for head in list(puzzle.unsolved_idxs):
        head_pos = pos(head)
        head_free = free(head)
        for i in rec([head]):
            yield i

def xy_chain(puzzle):
    """ This loops over the puzzles xy link chains constraining """
    free = lambda x:puzzle.free_related_cells(x)
    for chain, val in xy_chain_links(puzzle):
        head,tail = chain[0],chain[-1]
        to_notify = (free(head)&free(tail))-set(chain)
        should_notify = False
        for i in to_notify:
            if puzzle.remove_index_possibilities(i, val):
                puzzle.stats.inc('xy-chain')
                should_notify = True
        if should_notify:
            logging.debug("XY Chain%s: removing %s from %s - %s"%
                      (chain ,val, to_notify, map(puzzle.get_possibilities,chain)))
            return True

def x_chain(puzzle):
    """
    http://www.sudopedia.org/wiki/X-Chain
    """
    pass

def strong_links (puzzle,from_idx):
    pos = lambda x:puzzle.get_possibilities(x)
    from_pos = pos(from_idx)

    e=((to, v)
       for freefn in [puzzle.free_in_square,
                      puzzle.free_in_col,
                      puzzle.free_in_row]
       for freeidxs in [freefn(from_idx)]
       for to in freeidxs
       for v in from_pos & pos(to)

       # V can only be in from or to
       # so it is a strong link
       if v not in pos(*freeidxs-set([from_idx,to]))

       )
    return e

def weak_links(puzzle, from_idx):
    pos = lambda x:puzzle.get_possibilities(x)
    from_pos = pos(from_idx)

    e=((to, v)
       for freefn in [puzzle.free_in_square,
                      puzzle.free_in_col,
                      puzzle.free_in_row]
       for freeidxs in [freefn(from_idx)]
       for to in freeidxs
       for v in from_pos & pos(to)
       # any cell in a house that shares a value with
       # this index is weakly linked
       )
    return e



def alternating_chains(puzzle):
    def links(idx,chain):
        if len(chain)%2==0 : return puzzle.strong_links(idx)
        else: return puzzle.weak_links(idx)

    def rec (idx,chain=[]):
        for link in links(idx,chain):
            newc = chain+[link]
            yield newc
            for chain in rec(link,newc):
                yield chain

    for i in list(puzzle.unsolved_idxs):
        if puzzle.index_solved(i): continue
        for chain in rec(i):
            yield chain

def fishy_cycles(puzzle):
    """
    XWING / Swordfish generalization:
    http://www.sudopedia.org/wiki/Fishy_Cycle
    """
    for chain in puzzle.alternating_chains():
        # look for xwing cycles
        if len(chain) != 5 or chain[0] != chain[-1] \
                or len(set(chain))!=4:
            continue




def xy_wing(puzzle):
    """
        Implements the XY-wing sudoku strategy
        http://www.sudopedia.org/wiki/XY-Wing
    """
    free = lambda x:puzzle.free_related_cells(x)
    pos = lambda x:puzzle.get_possibilities(x)

    xy_links = (((i1,i2,i3),p1&p3)
                 for i1 in list(puzzle.unsolved_idxs)
                 for p1 in [pos(i1)]
                 for i2 in free(i1)-set([i1])
                 for p2 in [pos(i2)]
                 for i3 in free(i2)-set([i1,i2])
                 for p3 in [pos(i3)]
                 if len(p1) == 2 and len(p2)==2 and len(p3)==2
                 and len(p1&p2)==1 and len(p2&p3)==1 and len(p1&p3)==1
                 and len(p1&p2&p3)==0)
    for idxs , sharedv in xy_links:
        # the related nodes that i1 and i3 share that
        # are not in the link
        to_notify = (free(idxs[0])&free(idxs[-1]))-set(idxs)
        should_notify = False
        for i in to_notify:
            if puzzle.remove_index_possibilities(i,sharedv):
                puzzle.stats.inc('xy-wing')
                should_notify = True
        if(should_notify):
            logging.debug("XYWing%s: removing %s from %s" %
                          (idxs, sharedv, to_notify))
            return True


constraintsToRun = [
    single_possibility,
    run_constraints_across_houses(unique_possibility),

    run_constraints_across_houses(set_exclusions),
    xy_chain,
    xwing_col_constraint,
    xwing_row_constraint,

    # These shouldnt ever produce anything
    # squeeze,
    # run_constraints_across_houses(naked_set_exclusions),
    # xy_wing,
]
