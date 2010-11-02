from StringIO import StringIO
import re, traceback, types, itertools
import cProfile, pstats, time
import logging
from copy import deepcopy, copy
import puzzles, puzzles2


logging.basicConfig(level=logging.INFO)

PVALS = set(range(1,10))
PIDXS = set(range(0,9))

def every_combo(inp):
    for i in range(2,len(inp)):
        for v in itertools.combinations(inp,i):
            yield v

class Index (object):
    def __init__(self,row,col):
        self.row,self.col = row,col
    def __eq__(self, other):
        return self.row == other.row and self.col == other.col
    def __str__(self):
        return "<%s,%s>"%(self.row, self.col)
    def __repr__(self):
        return "<%s,%s>"%(self.row, self.col)
    def __hash__(self):
        return self.row*100+self.col
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

class Stats (Ref):
    def __init__(self,**kws):
        Ref.__init__(self, **kws)
    def inc(self,k,v=1):
        return setattr(self, k, getattr(self,k,0)+v)

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
        return sorted([Box(idx,self.index_possibilities(idx))
                       for idx in puzzle_range
                       if not self.square_solved(idx)],
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

#        logging.info("Couldn't solve board via constraints, %s\nStarting to guess",
#                     self.print_help())
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
            
    def square_solved(self,idx):
        return self.puzzle[idx.row][idx.col]

    def clear_puzzle_possibility_cache(self):
        self.possibility_hash={} #reset IP memoization

    def set_puzzle_val(self, idx, v):
        #self.clear_puzzle_possibility_cache()
        self.puzzle[idx.row][idx.col] = v
        self.set_index_possibilities(idx, set([v]))
        self.unsolved_idxs.remove(idx)
    
    def constrain(self):
        new_constraint = False

        constraints = [
            self.unique_possibility_in_row,
            self.unique_possibility_in_col,
            self.unique_possibility_in_square,


            # These seem to be not constraing over the others
            # self.squeeze_col, self.squeeze_row,

            ]
        def run_set_constraints():
            for j in PIDXS:
                idx = Index(0,j)
                self.xwing_col_constraint(self.index_possibilities(idx),idx)
                self.set_exclusion_in_col(self.index_possibilities(idx),idx)
                self.naked_sets_exclusion_in_col(self.index_possibilities(idx),idx)

            for i in PIDXS:
                idx = Index(i,0)
                self.xwing_row_constraint(self.index_possibilities(idx),idx)
                self.set_exclusion_in_row(self.index_possibilities(idx),idx)
                self.naked_sets_exclusion_in_row(self.index_possibilities(idx),idx)

            for i in range(0,3):
                for j in range(0,3):
                    idx = Index(i*3,j*3)
                    self.set_exclusion_in_square(self.index_possibilities(idx),idx)
                    self.naked_sets_exclusion_in_square(self.index_possibilities(idx),idx)
            
        def fn():
            self._constrained_this_cycle = False
            self.stats.constraint_steps+=1
            for cons in constraints:
                # copy the set so we can remove the currently
                # inspected index if nec
                for idx in list(self.unsolved_idxs):
                    if self.square_solved(idx): 
                        self.unsolved_idxs.remove(idx)
                        continue
                    p = self.index_possibilities(idx)
                    if len(p)==1: self.stats.inc('single_possibility')
                    elif len(p)>1: p = cons(p, idx)
                    # start over reconstraining
                    if len(p)==1:
                        for i in self.free_related_cells(idx):
                            if i == idx: continue                            
                            self.remove_index_possibilities(i, p)
                        self.set_puzzle_val(idx,list(p)[0])
                    elif len(p)==0: raise NoPossibleValues(idx)
            run_set_constraints()
            return self._constrained_this_cycle
        while(fn()): pass
        
    def free_in_row(self, idx_in):
        return [idx 
                for j in PIDXS
                for idx in [Index(idx_in.row,j)]
                if not self.square_solved(idx)]

    def free_in_col(self, idx_in):
        return [idx
                for i in PIDXS
                for idx in [Index(i,idx_in.col)]
                if not self.square_solved(idx)]

    def free_in_square(self, idx_in):
        return [idx 
                for idx in square(idx_in)
                if not self.square_solved(idx)]

    def free_related_cells(self, idx):
        return self.free_in_row(idx)+self.free_in_col(idx)+self.free_in_square(idx)

    def free_related_possibilities(self, idx):
        return [self.index_possibilities(i)
                for i in self.free_related_cells(idx)
                if i!=idx]

    def closed_square_row(self, idx):
        return [i for i in square_idxs(idx.row)
                if self.square_solved(Index(i, idx.col))]

    def closed_square_col(self, idx):
        return [j for j in square_idxs(idx.col)
                if self.square_solved(Index(idx.row, j))]

    def is_in_row(self, val, row):
        for j in PIDXS: 
            if self.puzzle[row][j] == val: return True

    def is_in_col(self, val, col):
        for i in PIDXS: 
            if self.puzzle[i][col] == val: return True

    def xwing_col_constraint(self, pos, idx):
        # buid a collection of row->possibility->number of times that
        # possibility occurs
        posCounts = [[PosCount(v) for v in PVALS]
                     for i in PIDXS]
        for i in self.unsolved_idxs:
            for val in self.index_possibilities(i):
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
            pos = pos - sv
            others = (set(self.free_in_col(c1))|set(self.free_in_col(c2)))-set([c1,c2,c3,c4])
            for o in others:
                if self.remove_index_possibilities(o,sv):
                    self.stats.inc('xwing_col')
        return pos

    def xwing_row_constraint(self, pos, idx):
        posCounts = [[PosCount(v) for v in PVALS]
                     for i in PIDXS]
        for i in self.unsolved_idxs:
            for val in self.index_possibilities(i):
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
            pos = pos - sv
            others = (set(self.free_in_row(c1))|set(self.free_in_row(c3)))-set([c1,c2,c3,c4])
            for o in others:
                if self.remove_index_possibilities(o,sv):
                    self.stats.inc('xwing_row')
        return pos

    def squeeze_col(self, pos, idx):
        """ constrain possibilities by squeezing
        http://www.chessandpoker.com/sudoku-strategy-guide.html
        """
        if len(self.closed_square_col(idx))==2: # two closed columns
            idxs = square_idxs(idx.row)
            idxs.remove(idx.row)
            for v in pos:
                if self.is_in_row(v, idxs[0]) and self.is_in_row(v,idxs[1]):
                    #print "Squeezing <%s,%s> to %s" % (row, col, v)
                    self.stats.inc('squeeze_col')
                    return set([v])
        return pos

    def squeeze_row(self, pos, idx):
        if len(self.closed_square_row(idx))==2: # two closed rows
            idxs = square_idxs(idx.col)
            idxs.remove(idx.col)
            for v in pos:
                if self.is_in_col(v, idxs[0]) and self.is_in_col(v,idxs[1]):
                    #print "Squeezing <%s,%s> to %s" % (row, col, v)
                    self.stats.inc('squeeze_row')
                    return set([v])
        return pos

    def _unique_possibility_helper(self, cells, pos, name):
        for v in pos:
            not_allowed_elsewhere = \
                all(not v in self.index_possibilities(i)
                    for i in cells)
            if not_allowed_elsewhere:
                self.stats.inc(name)
                return set([v])
        return pos

    def unique_possibility_in_square(self,pos,idx):
        """ constrain possibilities by crosshatching
        http://www.chessandpoker.com/sudoku-strategy-guide.html
        """
        cells = self.free_in_square(idx)
        cells.remove(idx)
        return self._unique_possibility_helper(  cells, pos, 'unique_in_square')

    def unique_possibility_in_row(self,pos,idx):
        """ constrain possibilities by crosshatching
        http://www.chessandpoker.com/sudoku-strategy-guide.html
        """
        cells = self.free_in_row(idx)
        cells.remove(idx)
        return self._unique_possibility_helper(cells, pos, 'unique_in_row')

    def unique_possibility_in_col(self,pos,idx):
        cells = self.free_in_col(idx)
        cells.remove(idx)
        return self._unique_possibility_helper(cells, pos, 'unique_in_col')

    def _sets_helper(self, free_list, pos, name):
        """ If a set of cells are the only cells that can hold a 
        set of values of equal length, then those values must be 
        in those squares. So remove all other possibilities from
        those cells
        """
        # count the possibilities for each free square
        pcnts = [PosCount(v) for v in PVALS]
        for idx in free_list:
            for v in self.index_possibilities(idx):
                pcnts[v-1].idxs.append(idx)

        # remove any values that are not possible and close this
        pcnts = Ref(it=[i for i in pcnts if len(i)>1])
        
        sets = []
        # look for sets by looking at every combination
        # of values, and finding ones that share a common set 
        # of indexs exclusively
        def fn():
            cmbs = every_combo(pcnts.it)
            for cmb in cmbs:
                #union all the indexes for the value set we are looking at
                idxs = set.union(*map(set,cmb)) 
                vals = set(pcnt.val for pcnt in cmb)
                others = (set(free_list) - set(idxs))

                # we are looking for boxes that can share a specific set
                # of values exclusively so we need to be able to put
                # each value in a box
                if len(idxs) != len(vals) or len(others)==0: continue

                other_pos = set.union(*[self.index_possibilities(idx)
                                        for idx in others])
            
                # none of our values should be placeable elsewhere
                set_is_related = all(v not in other_pos 
                                     for v in vals)

                # trying to pull naked sets into here
                # idx_pos = [self.index_possibilities(idx)
                #            for idx in idxs]
                # fullestpos = max(idx_pos,key=len)
                # set_is_related |= all(p <= fullestpos
                #                      for p in idx_pos)
                
                # Sanity: none of the values we are 
                # removing can only be here

                # set_is_related &= all(v in other_pos
                #                      for i in idxs
                #                      for v in self.index_possibilities(i)-vals)
            
                if set_is_related:
                    sets.append((vals,idxs))
                    pcnts.it = [pcnt for pcnt in pcnts.it
                                if pcnt.val not in vals]
                    #return True
        while( len(pcnts.it) > 1 and fn()): pass
        
        for vals,idxs in sets:
            others = (set(free_list) - set(idxs))
            # constrain the related indexes in the set
            to_inc = False
            for idx in idxs: # our indexes cant have anything but our values
                to_inc |= self.set_index_possibilities(
                    idx, vals&self.index_possibilities(idx))
            for idx in others: # other indexes cant have our values
                to_inc |= self.remove_index_possibilities(idx, vals)
            if to_inc:
                self.stats.inc(name)
        return pos

    def set_exclusion_in_col(self,pos,idx):
        fic = self.free_in_col(idx)
        return self._sets_helper(fic,pos,'sets_col_constraint')

    def set_exclusion_in_row(self,pos,idx):
        fic = self.free_in_row(idx)
        return self._sets_helper(fic,pos,'sets_row_constraint')

    def set_exclusion_in_square(self,pos,idx):
        fic = self.free_in_square(idx)
        return self._sets_helper(fic,pos,'sets_square_constraint')

    def _naked_sets_helper(self, free_list, pos, name):
        free_list.sort(key=self.index_possibilities)
        # group free squares by shared possiblity lists
        groups = [(i,gl) 
                  for i,g in itertools.groupby(free_list, self.index_possibilities)
                  for gl in [list(g)]]
        kfn = lambda x: len(x[0])
        groups.sort(key=kfn)
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
            for cell in set(free_list)-set(gl):
                if self.remove_index_possibilities(cell,not_pos):
                    self.stats.inc(name+'_contraint')
        return pos
        
    def naked_sets_exclusion_in_col(self,pos,idx):
        fic = self.free_in_col(idx)
        return self._naked_sets_helper(fic,pos,'naked_sets_col')

    def naked_sets_exclusion_in_row(self,pos,idx):
        fic = self.free_in_row(idx)
        return self._naked_sets_helper(fic,pos,'naked_sets_row')

    def naked_sets_exclusion_in_square(self,pos,idx):
        fic = self.free_in_square(idx)
        return self._naked_sets_helper(fic,pos,'naked_sets_square')

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
        if old!=pos: 
            self._constrained_this_cycle=True
            self._constrained_this_set = True
        return self._constrained_this_set

    def remove_index_possibilities(self,idx,pos):
        new_pos = self.index_possibilities(idx)-pos
        return self.set_index_possibilities(idx, new_pos)
        
    def index_possibilities(self,idx):
        if self.possibility_hash.has_key(idx):
            return self.possibility_hash[idx]
        v = self.square_solved(idx)
        if v: return set([v])
        pos = PVALS - self.index_constraints(idx)
        self.set_index_possibilities(idx, pos)
        return pos

    def is_solved(self):
        for i in puzzle_range: 
            if not self.square_solved(i): return False
        return self

    def status(self):
        s=StringIO()
        if self.is_solved():
            s.write('Solved Puzzle: \n')
        else:
            s.write('Unsolved Puzzle:\n')
        stats = deepcopy(vars(self.stats))
        del stats['constraint_steps']
        del stats['puzzle_branches']
        s.write("  %s - Constraint Cycles\n" % self.stats.constraint_steps)
        s.write("  %s - Branches\n\n" % self.stats.puzzle_branches)
        items = stats.items()
        items.sort()
        for k,v in items:
            s.write('  %s : %s \n' % (k,v))
        s = s.getvalue()
        #logging.info(s)
        return s

    def __str__(self):
        s = StringIO()
        s.write("-------------------------------\n")
        s.write(self.status())
        s.write("-------------------------------\n")
        for i in PIDXS:
            s.write('|')
            for j in PIDXS:
                s.write(' ')
                if self.square_solved(Index(i,j)): s.write(self.puzzle[i][j])
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
                pos = self.index_possibilities(idx)
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
    puz = puzzles.puzzles
    for p in puz :
        print "Starting puzzle %s" % i
        p = read_puzzle(p)
        p.start = time.time()
        s = solve_puzzle(p)
        print s
        ptime = time.time()-p.start
        total_time += ptime
        print "Done with puzzle %s in %s sec" % (i, ptime)
        i+=1
    print "Done with %d puzzles in %s sec" % (len(puz), total_time)

     
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
