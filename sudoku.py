from StringIO import StringIO
import re, traceback, types, itertools
import cProfile, pstats, time
import logging
from copy import deepcopy, copy
import puzzles, puzzles2

logging.basicConfig(level=logging.info)

PVALS = set(range(1,10))
PIDXS = set(range(0,9))
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

class Memoize(object):
    """Memoize(fn) - an instance which acts like fn but memoizes its arguments
       Will only work on functions with non-mutable arguments
    """
    def __init__(self, fn):
        self.fn = fn
        self.memo = {}
    def __call__(self, *args):
        if not self.memo.has_key(args):
            self.memo[args] = self.fn(*args)
        return self.memo[args]

class PosCount(object):
    def __init__(self, cnt=0, idxs=None):
        self.cnt,self.idxs=cnt,idxs or []
    def __repr__(self):
        return "|%d|"%self.cnt
    def __str__(self):
        return "|%d|"%self.cnt

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

class Stats (object):
    def __init__(self,**kws):
        for k,v in kws.items():
            setattr(self, k, v)
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
        self.ip = Memoize(Sudoku.index_possibilites)
        self.index_possibilites = types.MethodType(self.ip, self, Sudoku)
    
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
        return sorted([Box(idx,self.index_possibilites(idx))
                       for idx in puzzle_range
                       if not self.square_solved(idx)],
                      key=len)

    def search(self):
        try:
            self.constrain()
        except NoPossibleValues,e:
            if self.parent: raise e
            else:
                print "ERROR ON BOARD:\n",self
                raise e
        if self.is_solved(): return self
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
            self.puzzle = deepcopy(sol.puzzle)
            self.status()
        else:
            print self
            raise Exception("Puzzle Not Solved...")
            
    def square_solved(self,idx):
        return self.puzzle[idx.row][idx.col]

    def clear_puzzle_possibility_cache(self):
        self.ip.memo={} #reset IP memoization

    def set_puzzle_val(self, idx, v):
        self.clear_puzzle_possibility_cache()
        self.puzzle[idx.row][idx.col] = v
        self.unsolved_idxs.remove(idx)
    
    def constrain(self):
        new_constraint = False
        constraints = [
            self.unique_possibility_in_row,
            self.unique_possibility_in_col,
            self.unique_possibility_in_square,
            self.naked_sets_exclusion_in_col,
            self.naked_sets_exclusion_in_square,
            self.naked_sets_exclusion_in_row,
            self.xwing_col_constraint,
            self.xwing_row_constraint,

            # These seem to be not constraing over the others
            self.squeeze_col,
            self.squeeze_row,
            ]
        def fn():
            self._constrained_this_cycle = False
            for cons in constraints:
                # copy the set so we can remove the currently inspected index if nec
                for idx in list(self.unsolved_idxs):
                    self.stats.constraint_steps+=1
                    if self.square_solved(idx): 
                        self.unsolved_idxs.remove(idx)
                        continue
                    p = self.index_possibilites(idx)
                    if len(p)==1: self.stats.inc('single_possibility')
                    elif len(p)>1: p = cons(p, idx)
                    # start over reconstraining
                    if len(p)==1: 
                        self.set_puzzle_val(idx,p.pop())
                        return True
                    elif len(p)==0: raise NoPossibleValues(idx)
            return self._constrained_this_cycle
        while(fn()): pass
        
    def free_in_row(self, row):
        return [idx 
                for j in PIDXS
                for idx in [Index(row,j)]
                if not self.square_solved(idx)]

    def free_in_col(self, col):
        return [idx
                for i in PIDXS
                for idx in [Index(i,col)]
                if not self.square_solved(idx)]

    def free_in_square(self, idx_in):
        return [idx 
                for idx in square(idx_in)
                if not self.square_solved(idx)]

    def free_related_cells(self, idx):
        return self.free_in_row(idx.row)+self.free_in_col(idx.col)+self.free_in_square(idx)

    def free_related_possibilities(self, idx):
        return [self.index_possibilites(i)
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

    def xwing_row_constraint(self, pos, idx):
        posCounts = [[PosCount() for i in range(0,9)]
                     for i in range(0,9)]
        for i in self.unsolved_idxs:
            for val in self.index_possibilites(i):
                posCounts[i.row][val-1].cnt+=1
                posCounts[i.row][val-1].idxs.append(i)
        p = deepcopy(pos)

        for val in p:
            i1=None
            i2=None
            for i in PIDXS:
                if i!=idx.row and posCounts[i][val-1].cnt==2: # 2 cells share this pos
                    if i1: i2=i
                    else: i1=i
            if i1 and i2:
                c1,c2 = posCounts[i1][val-1].idxs
                c3,c4 = posCounts[i2][val-1].idxs
                if c1.col>c2.col: c1,c2 = c2,c1 
                if c3.col>c4.col: c3,c4 = c4,c3
                if c1.col!=c3.col or c2.col!=c4.col: continue # not an xwing square
                if c1.col!=idx.col and c2.col!=idx.col: continue # not relevant to me
                # we have an xwing square
                pos = pos - set([val])
                if len(pos) == 1 :
                    #print "XWING : <%s,%s> to %s\n" % (row,col,pos)
                    #print c1, self.index_possibilites(*c1)
                    #print c2, self.index_possibilites(*c2)
                    #print c3, self.index_possibilites(*c3)
                    #print c4, self.index_possibilites(*c4)
                    self.stats.inc('xwing_row')
                    return pos
        return pos

    def xwing_col_constraint(self, pos, idx):
        posCounts = [[PosCount() for i in range(0,9)]
                     for i in range(0,9)]
        for i in self.unsolved_idxs:
            for val in self.index_possibilites(idx):
                posCounts[i.col][val-1].cnt+=1
                posCounts[i.col][val-1].idxs.append(i)
        p = deepcopy(pos)

        for val in p:
            j1=None
            j2=None
            for j in PIDXS:
                if j!=idx.col and posCounts[j][val-1].cnt==2: # 2 cells share this pos
                    if j1: j2=j
                    else: j1=j
            if j1 and j2:
                c1,c2 = posCounts[j1][val-1].idxs
                c3,c4 = posCounts[j2][val-1].idxs
                if c1.col>c2.col: c1,c2 = c2,c1 
                if c3.col>c4.col: c3,c4 = c4,c3
                if c1.col!=c3.col or c2.col!=c4.col: continue # not an xwing square
                if c1.col!=idx.col and c2.col!=idx.col: continue # not relevant to me
                # we have an xwing square
                pos = pos - set([val])
                if len(pos) == 1 : 
                    self.stats.inc('xwing_col')
                    return pos
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
                all([not v in self.index_possibilites(i)
                     for i in cells])
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
        return self._unique_possibility_helper( cells, pos, 'unique_in_square')

    def unique_possibility_in_row(self,pos,idx):
        """ constrain possibilities by crosshatching
        http://www.chessandpoker.com/sudoku-strategy-guide.html
        """
        cells = self.free_in_row(idx.row)
        cells.remove(idx)
        return self._unique_possibility_helper(cells, pos, 'unique_in_row')

    def unique_possibility_in_col(self,pos,idx):
        cells = self.free_in_col(idx.col)
        cells.remove(idx)
        return self._unique_possibility_helper(cells, pos, 'unique_in_col')

    def hidden_set_possibility_reduction(self):
        cells = list(self.unsolved_idxs)
        cells.sort(key=self.index_possibilites)
        # hidden sets
        #groups = [[self.index_possibilites(i) for i in gl]
        #          for p,g in itertools.groupby(free_list, self.index_possibilites)
        #          for gl in [list(g)]
        #          if len(gl) == len(i)]

    def _naked_sets_helper(self, free_list ,pos, name):
        free_list.sort(key=self.index_possibilites)
        # naked sets
        groups = [(i,gl) 
                  for i,g in itertools.groupby(free_list, self.index_possibilites)
                  for gl in [list(g)]
                  if len(gl) == len(i)]

        # if we know these possiblities are being
        # used up in the naked set, might as well remove them
        # from everyone elses possibilities
        #
        # I think this doesnt matter because we would be investigating from
        # another nodes perspective in a little while.  Proof of constraint
        # propogation working though I suppose
        for not_pos,gl in groups:
            for cell in free_list:
                if not cell in gl:
                    to_tell = self.index_possibilites(cell)
                    for i in not_pos: 
                        if i in to_tell: 
                            self._constrained_this_cycle=True
                            to_tell.remove(i)

        if len(groups)>0:
            # print "NAKED COL SET", groups
            for not_pos, idxs in groups:
                p = pos - not_pos
                if len(p)==1:
                    self.stats.inc(name)
                    return p
        return pos
        
    def naked_sets_exclusion_in_col(self,pos,idx):
        fic = self.free_in_col(idx.col)
        fic.remove(idx)
        return self._naked_sets_helper(fic,pos,'naked_sets_col')

    def naked_sets_exclusion_in_row(self,pos,idx):
        fic = self.free_in_row(idx.row)
        fic.remove(idx)
        return self._naked_sets_helper(fic,pos,'naked_sets_row')

    def naked_sets_exclusion_in_square(self,pos,idx):
        fic = self.free_in_square(idx)
        fic.remove(idx)
        return self._naked_sets_helper(fic,pos,'naked_sets_square')

    def index_constraints(self,idx):
        knowns = set()
        for i in PIDXS: knowns.add( self.puzzle[i][idx.col] )
        for i in PIDXS: knowns.add( self.puzzle[idx.row][i] )
        for i,j in square(idx): knowns.add( self.puzzle[i][j] )
        knowns.remove(None) # avoids many ifs
        return knowns

    def index_possibilites(self,idx):
        v = self.square_solved(idx)
        if v: return set([v])
        pos = PVALS - self.index_constraints(idx)
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
        logging.info(s)
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
    s.solve()
    assert s.is_solved()
    PUZZLE = s
    return s

def solve_some_puzzles():
    i = 1
    for p in puzzles.puzzles:
        print "Starting puzzle %s" % i
        p = read_puzzle(p)
        p.start = time.time()
        s = solve_puzzle(p)
        print s
        print "Done with puzzle %s in %s sec" % (i, time.time()-p.start)
        i+=1

     
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
