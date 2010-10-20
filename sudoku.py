from StringIO import StringIO
import re, traceback, types
import cProfile, pstats, time
import logging
from copy import deepcopy
import puzzles

logging.basicConfig(level=logging.info)

PVALS = set(range(1,10))
PIDXS = set(range(0,9))
def cross(l1, l2):
    return [[i,j] for i in l1 for j in l2]
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

def square_idxs(i):
    r = i / 3
    return range(r*3,r*3+3)

def square(row, col):
    return cross(square_idxs(row), square_idxs(col))

PUZZLE = None

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

class NoPossibleValues(Exception):
    def __init__(self, row, col):
        self.row,self.col = row,col
    def __str__(self):
        return "NoPossibleValues for <%d,%d>" % (self.row, self.col)

class Box (object):
    def __init__(self, row, column, val):
        self.row,self.column,self.val = row,column,val
    def __len__(self):
        if isinstance(self.val,int): return 1
        elif not self.val: return 0
        return len(self.val)
    def __str__(self):
        return "Box(%s,%s,%s)"%(self.row,self.column,self.val)

class Stats (object):
    def __init__(self,**kws):
        for k,v in kws.items():
            setattr(self, k, v)

class Sudoku (object):
    def __init__(self, puzzle, parent=None, depth=1,
                 start=None, unsolved_idxs=None,
                 stats=None):
        self.stats = stats or Stats(puzzle_branches=1, constraint_steps=0, row_squeezes=0,
                                    col_squeezes=0, single_possiblities=0, unique_in_row=0,
                                    unique_in_col=0,unique_in_square=0)
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
            c.puzzle[box.row][box.column] = new_val
        return c

    def open_boxes(self):
        return sorted([Box(i,j,self.index_possibilites(i,j))
                       for i,j in puzzle_range
                       if not self.square_solved(i,j)],
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
        assert sol and sol.is_solved()
        if sol and sol.is_solved():
            self.puzzle = deepcopy(sol.puzzle)
            self.status()
            
    def square_solved(self,row, col):
        return self.puzzle[row][col]

    def set_puzzle_val(self, row, col, v):
        self.ip.memo={} #reset IP memoization
        self.puzzle[row][col] = v
        self.unsolved_idxs.remove([row,col])
    
    def constrain(self):
        new_constraint = False
        constraints = [
            self.single_possibility_constraint,
            self.squeeze_col,
            self.squeeze_row,
            self.value_not_placeable_in_square,
            self.value_not_placeable_in_row,
            self.value_not_placeable_in_col,
            ]
        self.stats.constraint_steps+=1
        for cons in constraints:
            for i,j in self.unsolved_idxs:
                if self.square_solved(i,j): 
                    self.unsolved_idxs.remove([i,j])
                    continue
                p = cons(self.index_possibilites(i, j), i, j)
                if len(p)==1:
                    self.set_puzzle_val(i, j, p.pop())
                    new_constraint=True
                elif len(p)==0: raise NoPossibleValues(i,j)

        if new_constraint: self.constrain()
        
    def free_in_row(self, row):
        return [[row,j] for j in PIDXS if not self.square_solved(row, j)]

    def free_in_col(self, col):
        return [[i,col] for i in PIDXS if not self.square_solved(i, col)]

    def free_in_square(self, row, col):
        return [[i,j] for i,j in square(row,col) if not self.square_solved(i, j)]

    def free_square_row(self, row, col):
        return [i for i in square_idxs(row) if not self.square_solved(i, col)]

    def free_square_col(self, row, col):
        return [j for j in square_idxs(col) if not self.square_solved(row, j)]

    def closed_square_row(self, row, col):
        return [i for i in square_idxs(row) if self.square_solved(i, col)]

    def closed_square_col(self, row, col):
        return [j for j in square_idxs(col) if self.square_solved(row, j)]

    def is_in_row(self, val, row):
        for j in PIDXS: 
            if self.puzzle[row][j] == val: return True

    def is_in_col(self, val, col):
        for i in PIDXS: 
            if self.puzzle[i][col] == val: return True

    def single_possibility_constraint(self, pos, row, col):
        if len(pos)==1: self.stats.single_possiblities+=1
        return pos

    def squeeze_col(self, pos, row, col):
        """ constrain possibilities by squeezing
        http://www.chessandpoker.com/sudoku-strategy-guide.html
        """
        if len(self.closed_square_col(row, col))==2: # two closed columns
            idxs = square_idxs(row)
            idxs.remove(row)
            for v in pos:
                if self.is_in_row(v, idxs[0]) and self.is_in_row(v,idxs[1]):
                    #print "Squeezing <%s,%s> to %s" % (row, col, v)
                    self.stats.col_squeezes+=1
                    return set([v])
        return pos

    def squeeze_row(self, pos, row, col):
        if len(self.closed_square_row(row, col))==2: # two closed rows
            idxs = square_idxs(col)
            idxs.remove(col)
            for v in pos:
                if self.is_in_col(v, idxs[0]) and self.is_in_col(v,idxs[1]):
                    #print "Squeezing <%s,%s> to %s" % (row, col, v)
                    self.stats.row_squeezes+=1
                    return set([v])
        return pos

    def value_not_placeable_in_square(self,pos,row,col):
        """ constrain possibilities by crosshatching
        http://www.chessandpoker.com/sudoku-strategy-guide.html
        """
        #unpos = deepcopy(pos)
        #print "Cross Hatching <%s,%s> to %s" % (row, col, v)
        for v in pos:
            not_allowed_elsewhere = True
            sqrs = self.free_in_square(row, col)
            sqrs.remove([row,col]) #remove me from the current square
            for i,j in sqrs:
                not_allowed_elsewhere &= not v in self.index_possibilites(i, j)
            if not_allowed_elsewhere:
                self.stats.unique_in_square+=1
                return set([v])
        return pos

    def value_not_placeable_in_row(self,pos,row,col):
        """ constrain possibilities by crosshatching
        http://www.chessandpoker.com/sudoku-strategy-guide.html
        """
        for v in pos:
            not_allowed_elsewhere = True
            
            for j in PIDXS - set([col]):
                not_allowed_elsewhere &= \
                    not v in self.index_possibilites(row, j)
            if not_allowed_elsewhere: 
                self.stats.unique_in_row+=1
                return set([v])
        return pos

    def value_not_placeable_in_col(self,pos,row,col):
        for v in pos:
            not_allowed_elsewhere = True
            for i in PIDXS - set([row]):
                not_allowed_elsewhere &= \
                    not v in self.index_possibilites(i, col)
            if not_allowed_elsewhere:
                self.stats.unique_in_col+=1
                return set([v])
        return pos

    def twins_exclusion_in_col(self,pos,row,col):
        pass

    def index_constraints(self,row,col):
        knowns = set()
        for i in PIDXS: knowns.add( self.puzzle[i][col] )
        for i in PIDXS: knowns.add( self.puzzle[row][i] )
        for i,j in square(row,col): knowns.add( self.puzzle[i][j] )
        knowns.remove(None) # avoids many ifs
        return knowns

    def index_possibilites(self,row,col):
        v = self.square_solved(row,col)
        if v: return set([v])
        pos = PVALS - self.index_constraints(row,col)
        return pos        

    def is_solved(self):
        for i,j in puzzle_range: 
            if not self.square_solved(i,j): return False
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
        for k,v in stats.items():
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
                if self.square_solved(i,j): s.write(self.puzzle[i][j])
                else: s.write( '.' )
                s.write(' ')
                if j%3==2: s.write('|')
            s.write('\n')
            if i%3==2: s.write("-------------------------------\n")
        return s.getvalue()
     
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
