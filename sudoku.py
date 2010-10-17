from StringIO import StringIO
medium_puzzle = """
4 61     
32 6 7  5
51
2 4   3
 679 258
  3   2 7
       79
6  5 4 32
     86 1
"""

very_hard_puzzle = """
  6 5
 1   4 6
49 1   23
 79 6   5
 5  1  3 
1   9 87
73   8 91
 6 9   8 
    3 4  
"""

PVALS = range(1,10)
PIDXS = range(0,9)


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

def cross(l1, l2):
    return [[i,j] for i in l1 for j in l2]

def square(row, col):
    r,c = row / 3, col / 3
    return cross(range(r*3,r*3+3), range(c*3,c*3+3))

class Sudoku (object):
    def __init__(self, puzzle):
        self.puzzle = puzzle
        print self
        self.constrain()
        print self
        
    def constrain(self):
        new_constraint = [True]
        def fn():
            new_constraint[0] = False
            for i in PIDXS:
                for j in PIDXS:
                    #already solved square
                    if isinstance(self.puzzle[i][j], int): continue
                    p = set(PVALS) - self.index_constraints(i,j)
                    if len(p)==1:
                        p = p.pop()
                        print "found constraint:",i,j,p
                        new_constraint[0]=True
                        self.puzzle[i][j] = p
                    elif len(p)==0: raise Exception("No possible values")
                    else: self.puzzle[i][j] = p
        while(new_constraint[0]): fn()

    def index_constraints(self,row,col):
        knowns = set()
        for i in PIDXS:
            if isinstance( self.puzzle[i][col], int):
                knowns.add( self.puzzle[i][col] )
        for i in PIDXS:
            if isinstance( self.puzzle[row][i], int):
                knowns.add( self.puzzle[row][i] )
        for i,j in square(row,col):
            if isinstance( self.puzzle[i][j], int):
                knowns.add( self.puzzle[i][j] )
        return knowns

    def is_solved(self):
        for i,j in cross(PIDXS,PIDXS):
            if not isinstance(self.puzzle[i][j], int):
                return False
        return True

    def __str__(self):
        s = StringIO()
        if self.is_solved():
            s.write("-------------------\n")
            s.write('Solved Puzzle: \n')
        s.write("-------------------\n")
        for i in PIDXS:
            s.write('|')
            for j in PIDXS:
                if isinstance( self.puzzle[i][j], int):
                    s.write( self.puzzle[i][j] )
                else: s.write( ' ' )
                if j%3==2: s.write('|')
                else: s.write(',')
            s.write('\n')
            if i%3==2: s.write("-------------------\n")
        return s.getvalue()
        
med = read_puzzle(medium_puzzle)
vhard = read_puzzle(very_hard_puzzle)
                

 

