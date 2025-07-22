"""
optimized_freecell.py
---------------------
基于 Heineman Staged Deepening (HSD) 的 FreeCell 求解器（局部复制 + 整型牌编码版）
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple, List, Iterable
import heapq, itertools, random, time
from deadlock_heuristic_module import deadlock_heuristic


# ------------------------------------------------------------
# 牌编码工具
# ------------------------------------------------------------
SUIT_ID = {"C": 0, "D": 1, "H": 2, "S": 3}
RANK_ID = {"A": 1, "J": 11, "Q": 12, "K": 13, **{str(i): i for i in range(2, 11)}}

def encode(card_str: str) -> int:          # e.g. "10D" → 0b0001_1010 = 26
    rank, suit = card_str[:-1], card_str[-1]
    return (SUIT_ID[suit] << 4) | RANK_ID[rank]

def rank(c: int) -> int:   return c & 0x0F                    # 1–13
def suit(c: int) -> int:   return c >> 4                      # 0–3
def color(c: int) -> int:  return suit(c) & 1                 # 0=黑(S,C)  1=红(H,D)

# ------------------------------------------------------------
@dataclass(frozen=True)
class State:
    cascades: Tuple[Tuple[int, ...], ...]        # 8 列
    freecells: Tuple[int, ...]                   # 4 个，空位 -1
    foundations: Tuple[int, int, int, int]       # 四花色已达最高 rank

    # ---------------- 移动 ----------------
    def move(self, mv: 'Move') -> 'State':
        cs = list(self.cascades)
        fc = list(self.freecells)
        fd = list(self.foundations)

        # ------- 取牌 -------
        if mv.src == 'c':
            col = list(cs[mv.si]); card = col.pop(); cs[mv.si] = tuple(col)
        elif mv.src == 'f':
            card = fc[mv.si];      fc[mv.si] = -1
        else:
            raise ValueError

        # ------- 放牌 -------
        if mv.dst == 'c':
            col = list(cs[mv.di]); col.append(card); cs[mv.di] = tuple(col)
        elif mv.dst == 'f':
            fc[mv.di] = card
        elif mv.dst == 'd':        # foundation
            s = suit(card); fd[s] = rank(card)
        else:
            raise ValueError

        return State(tuple(cs), tuple(fc), tuple(fd))

    # ---------------- 终局判断 ----------------
    def is_goal(self) -> bool:
        return all(len(col) == 0 for col in self.cascades) and all(x == -1 for x in self.freecells)

# ------------------------------------------------------------
@dataclass(frozen=True)
class Move:
    src: str  # 'c'ascade | 'f'reecell
    si: int
    dst: str  # 'c'ascade | 'f'reecell | 'd' foundation
    di: int

# ------------------------------------------------------------
def parse_deal(text: str) -> State:
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    cascades: List[List[int]] = [[] for _ in range(8)]
    for line in lines[1:]:
        idx, cards = line.split(':')
        col = int(idx.split()[1]) - 1
        if cards.strip():
            cascades[col] = [encode(c) for c in cards.strip().split()]
    return State(tuple(tuple(col) for col in cascades),
                 tuple([-1] * 4),
                 (0, 0, 0, 0))

# ------------------------------------------------------------
# 启发式
# ------------------------------------------------------------
def heuristic_hsdh(st: State) -> int:
    """Heineman 原启发式：牌面之上的阻挡牌计数"""
    total = 0
    need = [fd + 1 for fd in st.foundations]   # 每花色下一个需要的 rank
    for col in st.cascades:
        for depth, c in enumerate(reversed(col)):
            s = suit(c)
            if rank(c) == need[s]:
                total += depth
                break
    if st.freecells.count(-1) == 0 or 0 in st.foundations:
        total *= 2
    return total

def combined_h(st: State) -> int:
    h1 = heuristic_hsdh(st)
    h2 = deadlock_heuristic(st)
    h3 = 52 - sum(st.foundations)
    return h1 + 1000*h2 + 10*h3

# ------------------------------------------------------------
def legal_moves(st: State) -> Iterable[Move]:
    cs = st.cascades; fd = st.foundations; fc = st.freecells
    # 1. cascade → cascade
    for i, col in enumerate(cs):
        if not col: continue
        top = col[-1]
        for j, tgt in enumerate(cs):
            if i == j: continue
            if not tgt and col:                 # 移到空列
                yield Move('c', i, 'c', j)
            elif tgt:
                t = tgt[-1]
                if color(top) != color(t) and rank(top) == rank(t)-1:
                    yield Move('c', i, 'c', j)

    # 2. cascade → freecell
    for i, col in enumerate(cs):
        if col:
            for j,f in enumerate(fc):
                if f == -1:
                    yield Move('c', i, 'f', j)
                    break

    # 3. freecell → cascade
    for i, card in enumerate(fc):
        if card == -1: continue
        for j, tgt in enumerate(cs):
            if not tgt:
                yield Move('f', i, 'c', j)
            else:
                top = tgt[-1]
                if color(card)!=color(top) and rank(card)==rank(top)-1:
                    yield Move('f', i, 'c', j)

    # 4. cascade/freecell → foundation
    for i,col in enumerate(cs):
        if col:
            card = col[-1]; s=suit(card)
            if rank(card) == fd[s]+1:
                yield Move('c', i, 'd', 0)
    for i,card in enumerate(fc):
        if card!=-1:
            s=suit(card)
            if rank(card)==fd[s]+1:
                yield Move('f', i, 'd', 0)

# ------------------------------------------------------------
def dfs_k(state: State, k: int, seen: set) -> Tuple[List[State], bool]:
    stack = [(state, 0)]
    frontier: List[State] = []
    while stack:
        cur, depth = stack.pop()
        if cur in seen: continue
        seen.add(cur)
        if cur.is_goal(): return [], True
        if depth == k:
            frontier.append(cur); continue
        for mv in legal_moves(cur):
            stack.append((cur.move(mv), depth+1))
    return frontier, False

# ------------------------------------------------------------
def hsd_solver(init: State, k=4, N=50000, timeout=300) -> State | None:
    start = time.time()
    open_list: list[tuple[int,int,State]] = []
    counter = itertools.count()
    heapq.heappush(open_list, (combined_h(init), next(counter), init))
    tt: set[State] = {init}

    while open_list:
        if time.time() - start > timeout:
            print("⏰ Timeout"); return None

        # 90% 取最优，10% 随机
        if random.random() < 0.9:
            _,_,cur = heapq.heappop(open_list)
        else:
            idx=random.randint(0,len(open_list)-1)
            _,_,cur = open_list[idx]
            open_list[idx]=open_list[-1]; open_list.pop(); heapq.heapify(open_list)

        front, goal = dfs_k(cur, k, set())
        if goal: return cur
        for st in front:
            if st in tt: continue
            tt.add(st)
            heapq.heappush(open_list,(combined_h(st),next(counter),st))
            if len(tt) >= N: tt.clear()

    return None

# ------------------------------------------------------------
####################### 示例运行 ###############################
example = """
Deal 10:
  Cascade 1: 10D 4C KH 10C AS JC 5H
  Cascade 2: QH 6D 6S 7S JD 3S 2H
  Cascade 3: 2S KD 10S KC 3D 5D 3C
  Cascade 4: 9S 8S QD QC 5C 6H JH
  Cascade 5: 4S 7C 6C 7D 8D 4H
  Cascade 6: 4D 3H 2D 10H 5S AD
  Cascade 7: 2C 9H 9C JS 8H AC
  Cascade 8: 7H 8C 9D AH QS KS
"""

if __name__ == "__main__":

    state = parse_deal(example)
    print("Initial State:")
    print(state)

    # 参数设置
    k = 6
    N = 100000

    start = time.time()
    print("Solving...")
    try:
        result = hsd_solver(state, k, N, timeout=600)
    except TimeoutError as e:
        print(str(e))
        result = None

    print("Time:", time.time() - start)

    if result:
        print("Solved! Final State:")
        print(result)
    else:
        print("No solution found.")
