from StringIO import StringIO
import cProfile, pstats
import logging
from copy import deepcopy
import puzzles

logging.basicConfig(level=logging.info)

PVALS = range(1,10)
PIDXS = range(0,9)
def cross(l1, l2):
    return [[i,j] for i in l1 for j in l2]
puzzle_range = cross(PIDXS,PIDXS)

def tryint(v):
    try: return int(v)
    except: return None

def read_puzzle (s):
    puzzle = [[PVALS for j in PIDXS]
                   for i in PIDXS]
    partial_sol = s.splitlines()[1:]#skip first/last line
    i,j=0,0
    for row in partial_sol:
        j=0
        if i>8: continue
        for char in row:
            #print i,j,char
            if j>8: continue
            if tryint(char): puzzle[i][j] = int(char)
            j+=1
        i+=1
    return Sudoku(puzzle)

def square(row, col):
    r,c = row / 3, col / 3
    return cross(range(r*3,r*3+3), range(c*3,c*3+3))

def solve_puzzle(s):
    s = read_puzzle(s)
    s.solve()
    #print s
    print s.status()
    assert s.is_solved()
    return s

def solve_some_puzzles():
    for i in range(0,3):
        for p in puzzles.puzzles:
            s = solve_puzzle(p)

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
    def __init__(self, puzzle, parent=None):
        self.puzzle = puzzle
        self.parent = parent
        self.children = []
        self.count = 1
        self.constraint_steps = 0;
        self.solution = None
    
    def inc_count(self):
        if self.parent: self.parent.inc_count()
        self.count+=1
    def inc_cons(self):
        if self.parent: self.parent.inc_cons()
        self.constraint_steps+=1

    def make_child(self, box=None, new_val=None):
        logging.debug( "Making branch: box:%s val:%s"%(box, new_val) )
        self.inc_count()
        c = Sudoku(deepcopy(self.puzzle), self)
        if box and new_val:
            c.puzzle[box.row][box.column] = new_val
        self.children.append(c)
        return c

    def open_boxes(self):
        return sorted([Box(i,j,self.puzzle[i][j])
                       for i,j in puzzle_range
                       if not self.square_solved(i,j)],
                      key=len)

    def search(self):
        self.constrain()
        if self.is_solved():
            return self
        for box in self.open_boxes():
            for v in box.val:
                try:
                    c = self.make_child(box, v)
                    sol = c.search()
                    if isinstance(sol, Sudoku):
                        return sol
                except NoPossibleValues,e: pass

    def solve(self):
        self.solution = self.search()
        if self.solution:
            self.puzzle = deepcopy(self.solution.puzzle)
            self.status()
            
    
    def square_solved(self,row, col):
        return isinstance(self.puzzle[row][col], int)
    
    def constrain(self):
        new_constraint = [True]
        def fn():
            new_constraint[0] = False
            self.inc_cons()
            for i,j in puzzle_range:
                if self.square_solved(i,j): continue
                p = set(PVALS) - self.index_constraints(i,j)
                if len(p)==1:
                    p = p.pop()
                    new_constraint[0]=True
                    self.puzzle[i][j] = p
                elif len(p)==0: raise NoPossibleValues()
                else: self.puzzle[i][j] = p
        while(new_constraint[0]): fn()

    def index_constraints(self,row,col):
        knowns = set()
        for i in PIDXS:
            if self.square_solved(i,col):
                knowns.add( self.puzzle[i][col] )
        for i in PIDXS:
            if self.square_solved(row,i):
                knowns.add( self.puzzle[row][i] )
        for i,j in square(row,col):
            if self.square_solved(i,j):
                knowns.add( self.puzzle[i][j] )
        return knowns

    def is_solved(self):
        if self.solution: self.solution
        for i,j in puzzle_range:
            if not self.square_solved(i,j): return False
        return self

    def status(self):
        s = 'Solved Puzzle in %dc and %sb: \n' % \
            (self.constraint_steps, self.count)
        logging.info(s)
        return s

    def __str__(self):
        s = StringIO()
        if self.is_solved():
            s.write("-------------------\n")
            s.write('Solved Puzzle in %dc and %sb: \n' %
                    (self.constraint_steps, self.count))
        s.write("-------------------\n")
        for i in PIDXS:
            s.write('|')
            for j in PIDXS:
                if self.square_solved(i,j): s.write(self.puzzle[i][j])
                else: s.write( ' ' )
                if j%3==2: s.write('|')
                else: s.write(',')
            s.write('\n')
            if i%3==2: s.write("-------------------\n")
        return s.getvalue()
     
if __name__ == "__main__":
    solve_some_puzzles()
else:
    pf = 'sudoku.v1'
    cProfile.run('sudoku.solve_some_puzzles()', pf)
    p = pstats.Stats(pf)
    p.strip_dirs().sort_stats(-1)
    p.sort_stats('time').print_stats(10)

    

