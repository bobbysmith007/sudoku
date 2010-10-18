from StringIO import StringIO
import re, traceback
import cProfile, pstats, time
import logging
from copy import deepcopy
import puzzles

logging.basicConfig(level=logging.info)

PVALS = set(range(1,10))
PIDXS = range(0,9)
def cross(l1, l2):
    return [[i,j] for i in l1 for j in l2]
puzzle_range = cross(PIDXS,PIDXS)

def tryint(v):
    try: return int(v)
    except: return None

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


def square(row, col):
    r,c = row / 3, col / 3
    return cross(range(r*3,r*3+3), range(c*3,c*3+3))

def solve_puzzle(s):
    if isinstance(s,str):
        s = read_puzzle(s)
    s.solve()
    print s.status()
    assert s.is_solved()
    return s

def solve_some_puzzles():
    i = 1
    for p in puzzles.puzzles[0:4]:
        print "Starting puzzle %s" % i
        p = read_puzzle(p)
        print p
        p.start = time.time()
        s = solve_puzzle(p)
        print s
        print "Done with puzzle %s in %s sec" % (i, time.time()-p.start)
        i+=1

class NoPossibleValues(Exception): pass

class Box (object):
    def __init__(self, row, column, val):
        self.row,self.column,self.val = row,column,val
    def __len__(self):
        if isinstance(self.val,int): return 1
        elif not self.val: return 0
        return len(self.val)
    def __str__(self):
        return "Box(%s,%s,%s)"%(self.row,self.column,self.val)

class Sudoku (object):
    def __init__(self, puzzle, parent=None, depth=1, start=None, unsolved_idxs=None):
        self.puzzle = puzzle
        self.parent = parent
        self.depth = depth
        self.unsolved_idxs = unsolved_idxs or deepcopy(puzzle_range)
        self.start = start or time.time()
        self.count = 1
        self.constraint_steps = 0;
    
    def inc_count(self):
        if self.parent: self.parent.inc_count()
        self.count+=1

    def branch_count(self):
        if self.parent: return self.parent.branch_count()
        return self.count

    def inc_cons(self):
        if self.parent: self.parent.inc_cons()
        self.constraint_steps+=1

    def make_child(self, box=None, new_val=None):
        self.inc_count()
        idx = self.branch_count()
        if idx%1000==0:
            print "Making branch (idx:%d, depth:%d): %s val:%s - %ss"%(idx, self.depth, box, new_val, time.time()-self.start)
        c = Sudoku(deepcopy(self.puzzle), self, self.depth+1, self.start, deepcopy(self.unsolved_idxs))
        if box and new_val: 
            c.puzzle[box.row][box.column] = new_val
        return c

    def open_boxes(self):
        return sorted([Box(i,j,self.index_possibilites(i,j))
                       for i,j in puzzle_range
                       if not self.square_solved(i,j)],
                      key=len)

    def search(self):
        self.constrain()
        if self.is_solved():
            return self
        for box in self.open_boxes():
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
    
    def constrain(self):
        new_constraint = True
        while(new_constraint):
            new_constraint = False
            self.inc_cons()
            for i,j in self.unsolved_idxs:
                if self.square_solved(i,j): 
                    self.unsolved_idxs.remove([i,j])
                    continue
                p = self.index_possibilites(i,j)
                if len(p)==1:
                    p = p.pop()
                    self.puzzle[i][j] = p
                    new_constraint=True
                elif len(p)==0: raise NoPossibleValues()

    def index_constraints(self,row,col):
        knowns = set()
        for i in PIDXS:
            knowns.add( self.puzzle[i][col] )
        for i in PIDXS:
            knowns.add( self.puzzle[row][i] )
        for i,j in square(row,col):
            knowns.add( self.puzzle[i][j] )
        knowns.remove(None) # avoids many ifs
        return knowns

    def index_possibilites(self,row,col):
        return PVALS - self.index_constraints(row,col)

    def is_solved(self):
        for i,j in puzzle_range:
            if not self.square_solved(i,j): return False
        return self

    def status(self):
        s=None
        if self.is_solved():
            s = 'Solved Puzzle in %dc and %sb: \n' % \
                (self.constraint_steps, self.count)
        else:
            s = 'Unsolved Puzzle:\n%s' % self
        logging.info(s)
        return s

    def __str__(self):
        s = StringIO()
        if self.is_solved():
            s.write("-------------------------------\n")
            s.write('Solved Puzzle in %dc and %sb: \n' %
                    (self.constraint_steps, self.count))
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
    #puzzle0 = solve_puzzle(puzzles.puzzles[5])
    try:
        pf = 'sudoku.v2'
        cProfile.run('sudoku.solve_some_puzzles()', pf)
        p = pstats.Stats(pf)
        p.strip_dirs().sort_stats(-1)
        p.sort_stats('time').print_stats(10)
    except Exception,e:
        traceback.print_exc();

    

