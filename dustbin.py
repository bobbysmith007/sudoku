def row_strong_links(puzzle, from_idx):
    def pos(*x):
        return puzzle.get_possibilities(*x)
    from_pos = pos(from_idx)
    free = set(puzzle.free_in_row(from_idx)) - set([from_idx])
    for to in free:
        to_pos = pos(to)
        vals = from_pos & to_pos
        for v in vals:
            if models.is_row_strong_link(puzzle, from_idx, to, v):
                l = models.Link(puzzle, from_idx, to, v, True, from_pos)
                yield l


def col_strong_links(puzzle, from_idx):
    def pos(*x):
        return puzzle.get_possibilities(*x)
    from_pos = pos(from_idx)
    free = set(puzzle.free_in_col(from_idx)) - set([from_idx])
    for to in free:
        to_pos = pos(to)
        vals = from_pos & to_pos
        for v in vals:
            if models.is_col_strong_link(puzzle, from_idx, to, v):
                l = models.Link(puzzle, from_idx, to, v, True, from_pos)
                yield l


def square_strong_links(puzzle, from_idx):
    def pos(*x):
        return puzzle.get_possibilities(*x)
    from_pos = pos(from_idx)
    free = set(puzzle.free_in_square(from_idx)) - set([from_idx])
    for to in free:
        to_pos = pos(to)
        vals = from_pos & to_pos
        for v in vals:
            if models.is_square_strong_link(puzzle, from_idx, to, v):
                l = models.Link(puzzle, from_idx, to, v, True, from_pos)
               yield l

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
