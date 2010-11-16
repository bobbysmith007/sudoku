from StringIO import StringIO
import re, traceback, types
from itertools import combinations, groupby
import cProfile, pstats, time
import logging
from copy import deepcopy, copy
import puzzles, puzzles2


logging.basicConfig(level=logging.INFO)

PVALS = set(range(1,10))
PIDXS = set(range(0,9))

def are_distinct_sets (x,y):
    return len(x & y)==0

def combo_sets(inp, *lengths):
    if len(lengths)==0: lengths=range(2,len(inp)-1)
    for i in lengths:
        for v in combinations(inp,i):
            yield set(v)

class Index (object):
    def __init__(self,row,col):
        self.row,self.col = row,col
    def id (self):
        return self.row*100+self.col
    def __eq__(self, other):
        return self.row == other.row and self.col == other.col
    def __str__(self):
        return "<%s,%s>"%(self.row, self.col)
    def __repr__(self):
        return "<%s,%s>"%(self.row, self.col)
    def __hash__(self):
        return self.id()
    def __cmp__(self,other): 
        #so we can sort
        return self.id().__cmp__( other.id() )
    def __iter__(self):
        yield self.row
        yield self.col

def cross(l1, l2):
    return [Index(i,j) for i in l1 for j in l2]

puzzle_range = cross(PIDXS,PIDXS)

def tryint(v):
    try: return int(v)
    except: return None

class PosCount(object):
    def __init__(self, val=None, idxs=None):
        self.val,self.idxs=val,idxs or []
    def __len__ (self):
        return len(self.idxs)
    def __repr__(self):
        return "|%d|"%len(self)
    def __str__(self):
        return "|%d|"%len(self)
    def __iter__(self):
        return iter(self.idxs)

def square_idxs(i):
    r = i / 3
    return range(r*3,r*3+3)

def square(idx):
    return cross(square_idxs(idx.row), square_idxs(idx.col))

def share_a_row(*idxs):
    return all(idx.row==idxs[0].row
               for idx in idxs[1:])

def share_a_col(*idxs):
    return all(idx.col==idxs[0].col
               for idx in idxs[1:])

def share_a_square(*idxs):
    return all(idx.col/3==idxs[0].col/3 and idx.row/3==idxs[0].row/3
               for idx in idxs[1:])

class ConstrainedThisCycle(Exception):
    pass

class NoPossibleValues(Exception):
    def __init__(self, row=None, col=None):
        self.row,self.col = row,col
    def __str__(self):
        return "NoPossibleValues for <%s,%s>" % (self.row, self.col)

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

class Sudoku (object):
    def __init__(self, puzzle, parent=None, depth=1,
                 start=None, unsolved_idxs=None,
                 stats=None):
        self.stats = stats or Stats(puzzle_branches=1, constraint_steps=0)
        self.puzzle = puzzle
        self.parent = parent
        self.depth = depth
        self.unsolved_idxs = unsolved_idxs or deepcopy(puzzle_range)
        self.start = start or time.time()
        self.possibility_hash={}
        
    def make_child(self, box=None, new_val=None):
        self.stats.puzzle_branches+=1
        idx = self.stats.puzzle_branches
        if idx%1000==0:
            print "Making branch (idx:%d, depth:%d): %s val:%s - %ss" % \
                (idx, self.depth, box, new_val, time.time()-self.start)
        c = Sudoku(deepcopy(self.puzzle), self, self.depth+1, self.start, \
                       deepcopy(self.unsolved_idxs), self.stats)
        if box and new_val: 
            c.puzzle[box.idx.row][box.idx.col] = new_val
        return c

    def open_boxes(self):
        return sorted([Box(idx,self.get_possibilities(idx))
                       for idx in puzzle_range
                       if not self.index_solved(idx)],
                      key=len)

    def search(self):
        try:
            self.constrain()
        except NoPossibleValues,e:
            if self.parent: raise e
            else:
                print "ERROR ON BOARD:\n", self.print_help(),"\n\n",self
                raise e
        if self.is_solved(): return self

        logging.debug("Couldn't solve board via constraints, %s\n%s\nStarting to guess",
                     self, self.print_help())
        # really only care about the first open box as it WILL be one
        # of the values there if our model is correct up till now
        # otherwise any mistake is enough to backtrack
        box = self.open_boxes()[0]
        for v in box.val or []:
            try:
                c = self.make_child(box, v)
                sol = c.search()
                if sol: return sol
            except NoPossibleValues,e: pass

    def solve(self):
        sol = self.search()
        if sol and sol.is_solved():
            #self.puzzle = deepcopy(sol.puzzle)
            sol.status()
        else:
            print self.print_help(),"\n\n",self
            raise Exception("Puzzle Not Solved...")
        return sol
            
    def index_solved(self,idx):
        return self.puzzle[idx.row][idx.col]

    def clear_puzzle_possibility_cache(self):
        self.possibility_hash={} #reset IP memoization

    def set_puzzle_val(self, idx, v):
        #self.clear_puzzle_possibility_cache()
        self.puzzle[idx.row][idx.col] = v
        self.set_index_possibilities(idx, set([v]))
        if idx in self.unsolved_idxs:
            self.unsolved_idxs.remove(idx)
    
    def constrain(self):
        def run_constraints_across_houses(constraint):
            def fn():
                for j in PIDXS:
                    idxs = self.free_in_col(Index(0,j))
                    constraint(idxs,'col')
                    if self._constrained_this_cycle: return True

                for i in PIDXS:
                    idxs = self.free_in_row(Index(i,0))
                    constraint(idxs,'row')
                    if self._constrained_this_cycle: return True

                for i in range(0,3):
                    for j in range(0,3):
                        idxs = self.free_in_square(Index(i*3,j*3))
                        constraint(idxs,'square')
                        if self._constrained_this_cycle: return True
            return fn

        def find_solved_squares():
            self._constrained_this_cycle = False
            # copy the set so we can remove the currently
            # inspected index if nec
            for idx in list(self.unsolved_idxs):
                if self.index_solved(idx): 
                    if idx in self.unsolved_idxs:
                        self.unsolved_idxs.remove(idx)
                    continue
                p = self.get_possibilities(idx)
                if len(p)==1: 
                    self.stats.inc('single_possibility')
                    for i in self.free_related_cells(idx):
                        if i == idx: continue                            
                        self.remove_index_possibilities(i, p)
                    self.set_puzzle_val(idx,list(p)[0])
                elif len(p)==0: raise NoPossibleValues(idx)
            return self._constrained_this_cycle

        new_constraint = False

        constraints = [
            run_constraints_across_houses(self.unique_possibility),
            self.squeeze,
            run_constraints_across_houses(self.set_exclusions),
            self.xy_chain,
            self.xwing_col_constraint,
            self.xwing_row_constraint,

            # These shouldnt ever produce anything
            # run_constraints_across_houses(self.naked_set_exclusions),
            # self.xy_wing,
            ]
            

        def run_constraints():
            # Only resort to a higher reasoning 
            # when a lesser reasoning system fails us
            #
            # This should allow us to determine when 
            # a reasoning system is completely subsumed
            # by a more general one (xy_wing vs xy_chain)
            self._constrained_this_cycle = False
            def rec(cons):
                if len(cons) == 0: return
                cons[0]()
                if not self._constrained_this_cycle:
                    rec(cons[1:])
            rec(constraints)
            return self._constrained_this_cycle

        # whenever we are unable to find solved sqares
        # try running constraints till we succeed then
        # try solving squares again.  
        while(find_solved_squares() or run_constraints()):
            self.stats.constraint_steps+=1
        
    def free_in_row(self, idx_in):
        return set([idx 
                    for j in PIDXS
                    for idx in [Index(idx_in.row,j)]
                    if not self.index_solved(idx)])

    def free_in_col(self, idx_in):
        return set([idx
                    for i in PIDXS
                    for idx in [Index(i,idx_in.col)]
                    if not self.index_solved(idx)])

    def free_in_square(self, idx_in):
        return set([idx
                    for idx in square(idx_in)
                    if not self.index_solved(idx)])

    def free_related_cells(self, idx):
        return self.free_in_row(idx)| \
            self.free_in_col(idx)|self.free_in_square(idx)

    def free_related_possibilities(self, idx):
        idxs = self.free_related_cells(idx)-set(idx)
        return self.get_possibilities(*idxs)

    def closed_square_row(self, idx):
        return [i for i in square_idxs(idx.row)
                if self.index_solved(Index(i, idx.col))]

    def closed_square_col(self, idx):
        return [j for j in square_idxs(idx.col)
                if self.index_solved(Index(idx.row, j))]

    def is_in_row(self, val, row):
        for j in PIDXS: 
            if self.puzzle[row][j] == val: return True

    def is_in_col(self, val, col):
        for i in PIDXS: 
            if self.puzzle[i][col] == val: return True

    def xy_chain_links(self):
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
        free = lambda x:self.free_related_cells(x)
        pos = lambda x:self.get_possibilities(x)
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

        for head in self.unsolved_idxs:
            head_pos = pos(head)
            head_free = free(head)
            for i in rec([head]):
                yield i

    def xy_chain(self):
        """ This loops over the puzzles xy link chains constraining """
        free = lambda x:self.free_related_cells(x)
        for chain, val in self.xy_chain_links():
            head,tail = chain[0],chain[-1]
            to_notify = (free(head)&free(tail))-set(chain)
            should_notify = False
            for i in to_notify:
                if self.remove_index_possibilities(i, val):
                    self.stats.inc('xy-chain')
                    should_notify = True
            if should_notify:
                logging.debug("XY Chain%s: removing %s from %s - %s"%
                          (chain ,val, to_notify, map(self.get_possibilities,chain)))

    def x_chain(self):
        """ 
        http://www.sudopedia.org/wiki/X-Chain
        """
        pass

    def fishy_cycles(self):
        """ 
        XWING / Swordfish generalization:
        http://www.sudopedia.org/wiki/Fishy_Cycle
        """
        pass

    def xy_wing(self):
        """ 
            Implements the XY-wing sudoku strategy 
            http://www.sudopedia.org/wiki/XY-Wing
        """
        free = lambda x:self.free_related_cells(x)
        pos = lambda x:self.get_possibilities(x)

        xy_links = (((i1,i2,i3),p1&p3)
                     for i1 in self.unsolved_idxs
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
                if self.remove_index_possibilities(i,sharedv):
                    self.stats.inc('xy-wing')
                    should_notify = True
            if(should_notify):
                logging.debug("XYWing%s: removing %s from %s"%
                              (idxs ,sharedv,to_notify))

    def xwing_col_constraint(self):
        """
        Implements the XWing strategy looking through cols
        http://www.sudopedia.org/wiki/X-Wing
        """
        # buid a collection of row->possibility->number of times that
        # possibility occurs
        posCounts = [[PosCount(v) for v in PVALS]
                     for i in PIDXS]
        for i in self.unsolved_idxs:
            for val in self.get_possibilities(i):
                posCounts[i.row][val-1].idxs.append(i)

        gen = ((i1,i2,val)
               for i1 in PIDXS
               for i2 in range(i1+1,len(PIDXS))
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
            #print "XWING ",c1,c2,c3,c4,"\n",self.print_help()
            # we have an xwing square
            sv = set([val])
            others = (set(self.free_in_col(c1))|
                      set(self.free_in_col(c2)))-set([c1,c2,c3,c4])
            for o in others:
                if self.remove_index_possibilities(o,sv):
                    self.stats.inc('xwing_col')

    def xwing_row_constraint(self):
        """
        Implements the XWing strategy looking through rows
        http://www.sudopedia.org/wiki/X-Wing
        """
        posCounts = [[PosCount(v) for v in PVALS]
                     for i in PIDXS]
        for i in self.unsolved_idxs:
            for val in self.get_possibilities(i):
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
            # print "XWING ",c1,c2,c3,c4,"\n",self.print_help()
            # we have an xwing square
            sv = set([val])
            others = ( self.free_in_row(c1) | self.free_in_row(c3)) - \
                set([c1,c2,c3,c4])
            for o in others:
                if self.remove_index_possibilities(o,sv):
                    self.stats.inc('xwing_row')

    def squeeze(self):
        """ constrain possibilities by squeezing """
        def val_in_other_rows (v, idx):
            idxs = square_idxs(idx.row)
            idxs.remove(idx.row)
            return self.is_in_row(v, idxs[0]) and self.is_in_row(v,idxs[1])

        def val_in_other_cols (v, idx):
            idxs = square_idxs(idx.col)
            idxs.remove(idx.col)
            return self.is_in_col(v, idxs[0]) and self.is_in_col(v,idxs[1])

        gen = ((v,idx)
               for idx in self.unsolved_idxs
               for v in self.get_possibilities(idx)
               if val_in_other_cols(v, idx)
               and val_in_other_rows(v,idx))

        for v,idx in gen:
            if self.set_index_possibilities(idx, set([v])):
                self.stats.inc('squeeze')
            
    def unique_possibility(self, cells, name):
        gen = ((v,cell)
               for cell in cells
               for v in self.get_possibilities(cell)
               for others in [(cells - set([cell]))]
               if len(others)>0
               if v not in self.get_possibilities(*others))
        for v,cell in gen:
            if(self.set_index_possibilities(cell, set([v]))):
                self.stats.inc('unique_possibility_'+ name)

    def set_exclusions(self, free_list, name):
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
        unused_idxs = Ref(it=free_list)
        def handle_set (vals, idxs):
            """ constrain the related indexes in the set """

            others = set()
            # http://www.sudopedia.org/wiki/Locked_Candidates
            # if the set is locked we can add more others to the list:
            an_idx = list(idxs)[0]

            if share_a_square(*idxs):
                others |= self.free_in_square(an_idx)
            if share_a_col(*idxs):
                others |= self.free_in_col(an_idx)
            if share_a_row(*idxs):
                others |= self.free_in_row(an_idx)

            others = others - idxs
            to_inc = False
            for idx in idxs: # our indexes cant have anything but our values
                to_inc |= self.set_index_possibilities(
                    idx, vals & self.get_possibilities(idx))
            for idx in others: # other indexes cant have our values
                to_inc |= self.remove_index_possibilities(idx, vals)
            if to_inc:
                self.stats.inc('set_exclusions_'+name)
            return to_inc

        # look for sets by looking at every combination
        # of indexes, and finding ones that share a 
        # common subset of equal length of values
        for idxs in combo_sets(unused_idxs.it):
            idxs = set(idxs)
            idx_pos = self.get_possibilities(*idxs)
            
            #indexes not in the subset we are looking at
            others = (unused_idxs.it - idxs)
            other_pos = self.get_possibilities(*others)

            # every set of possibilities of the correct length should
            # be tested to see if they form a block of numbers that
            # could only be put here
            pos_sets = combo_sets(idx_pos, len(idxs))
            for vals in pos_sets:
                vals = set(vals)
                if are_distinct_sets(vals, other_pos):
                    handle_set(vals,idxs)

    def naked_set_exclusions(self, free_list, name):
        """ 
        This is deprecated code (replaced by sets exclusion) that looks for naked sets
        http://www.sudopedia.org/wiki/Naked_Subset
        """
        s = sorted(free_list,key=self.get_possibilities)
        # group free squares by shared possiblity lists
        kfn = lambda x: len(x[0])
        groups = sorted(((i,list(g))
                         for i,g in groupby(s, self.get_possibilities)),
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
                            # self.stats.inc(name+'_complex_constraint')
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
                if self.remove_index_possibilities(cell,not_pos):
                    self.stats.inc('naked_set_exclusions_'+name)
        
    def index_constraints(self,idx):
        knowns = set()
        for i in PIDXS: knowns.add( self.puzzle[i][idx.col] )
        for i in PIDXS: knowns.add( self.puzzle[idx.row][i] )
        for i,j in square(idx): knowns.add( self.puzzle[i][j] )
        knowns.remove(None) # avoids many ifs
        return knowns
    
    def set_index_possibilities(self,idx,pos):
        self._constrained_this_set = False
        if len(pos) == 0: raise NoPossibleValues(idx)
        old = self.possibility_hash.get(idx,set())
        self.possibility_hash[idx] = pos
#        if len(pos) == 1 and not self.index_solved(idx):
#            self.set_puzzle_val(idx,list(pos)[0])
        if old!=pos: 
            self._constrained_this_cycle=True
            self._constrained_this_set = True
        return self._constrained_this_set

    def remove_index_possibilities(self,idx,pos):
        new_pos = self.get_possibilities(idx)-pos
        return self.set_index_possibilities(idx, new_pos)
        
    def get_possibilities(self, *idxs):
        if len(idxs)==0: return set([])
        sets = [self.index_possibilities(i) for i in idxs]
        return set.union(*sets)

    def index_possibilities(self,idx):
        if self.possibility_hash.has_key(idx):
            return self.possibility_hash[idx]
        v = self.index_solved(idx)
        if v: return set([v])
        pos = PVALS - self.index_constraints(idx)
        self.set_index_possibilities(idx, pos)
        return pos

    def is_solved(self):
        for i in puzzle_range: 
            if not self.index_solved(i): return False
        return self

    def status(self):
        s=StringIO()
        if self.is_solved():
            s.write('Solved Puzzle: \n')
        else:
            s.write('Unsolved Puzzle:\n')
        s.write(str(self.stats))
        return s.getvalue()

    def __str__(self):
        s = StringIO()
        s.write("-------------------------------\n")
        s.write(self.status())
        s.write("-------------------------------\n")
        for i in PIDXS:
            s.write('|')
            for j in PIDXS:
                s.write(' ')
                if self.index_solved(Index(i,j)): s.write(self.puzzle[i][j])
                else: s.write( '.' )
                s.write(' ')
                if j%3==2: s.write('|')
            s.write('\n')
            if i%3==2: s.write("-------------------------------\n")
        return s.getvalue()

    def print_help(self):
        lb = "-------------------------------"\
            "---------------------------------"\
            "-------------------------------\n"
        s = StringIO()
        s.write(lb)
        s.write(self.status())
        s.write(lb)
        for i in PIDXS:
            s.write('||')
            for j in PIDXS:
                idx = Index(i,j)
                pos = self.get_possibilities(idx)
                for l in PVALS:
                    if l in pos: s.write(l)
                    else: s.write(' ')
                s.write('|')
                if j%3==2: s.write('|')
            s.write('\n')
            if i%3==2: s.write(lb)
        return s.getvalue()


def read_puzzle (s):
    puzzle = [[None for j in PIDXS]
              for i in PIDXS]
    #skip first/last line
    s = re.sub(r'\n\n+','\n',re.sub(r'-|\+|\|| |,',"",s))
    partial_sol = s.splitlines()[1:]
    i,j=0,0
    for row in partial_sol:
        j=0
        if i>8: continue
        for char in row:
            #print i,j,char
            if j>8: continue
            puzzle[i][j] = tryint(char)
            j+=1
        i+=1
    return Sudoku(puzzle)

PUZZLE = read_puzzle(puzzles.puzzles[0])

def solve_puzzle(s):
    global PUZZLE
    if isinstance(s,str):
        s = read_puzzle(s)
    p = s.solve()
    assert p.is_solved()
    PUZZLE = p
    return p

def solve_some_puzzles():
    i = 1
    total_time = 0
    puz = puzzles.puzzles#[8:]
    stats = Stats()
    for p in puz :
        print "Starting puzzle %s" % i
        p = read_puzzle(p)
        p.start = time.time()
        s = solve_puzzle(p)
        stats.inc(s.stats)
        print s
        ptime = time.time()-p.start
        total_time += ptime
        print "Done with puzzle %s in %s sec" % (i, ptime)
        i+=1
    print "\n -- TOTALS -- \nDone with %d puzzles in %s sec:\n%s" % \
        (len(puz), total_time, stats)

     
if __name__ == "__main__":
    solve_some_puzzles()
else:
    try:
        pf = 'sudoku.v4'
        cProfile.run('sudoku.solve_some_puzzles()', pf)
        p = pstats.Stats(pf)
        p.strip_dirs().sort_stats(-1)
        p.sort_stats('time').print_stats(10)
    except NameError,e:
        print "Reload module to run profiling"
        traceback.print_exc();
    except Exception, e:
        traceback.print_exc();
