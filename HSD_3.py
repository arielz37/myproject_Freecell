import time
import copy
import heapq
import itertools
import random
from collections import OrderedDict

from deadlock_heuristic_module import deadlock_heuristic


# 简单的测试牌局
simple_example = """
Deal 1:
  Cascade 1: AH
  Cascade 2: AD
  Cascade 3: AC
  Cascade 4: AS
  Cascade 5:
  Cascade 6:
  Cascade 7:
  Cascade 8:
"""

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


class State:
    """
    方案A：Copy-on-Write（局部浅拷贝）状态。
    - cascades: List[List[Card]]
    - freecells: List[Optional[Card]]
    - foundations: dict[str, List[Card]]
    """
    def __init__(self, cascades, freecells=None, foundations=None):
        # 这里不再无条件复制；假定传入者若需要隔离已自行复制
        self.cascades = cascades
        self.freecells = freecells if freecells is not None else [None] * 4
        self.foundations = foundations if foundations is not None else {'C': [], 'D': [], 'H': [], 'S': []}

    @staticmethod
    def from_text_block(text_block):
        lines = text_block.strip().split('\n')
        cascades = []
        for line in lines[1:]:  # skip "Deal X:"
            parts = line.split(':')[1].strip().split()
            cascade = [Card(code) for code in parts]
            cascades.append(cascade)
        return State(cascades)

    def __repr__(self):
        s = ""
        for i, cascade in enumerate(self.cascades):
            s += f"Cascade {i + 1}: {' '.join(str(card) for card in cascade)}\n"

        freecell_strs = [str(card) if card else "--" for card in self.freecells]
        s += f"Freecells: {' | '.join(freecell_strs)}\n"

        foundation_strs = []
        for suit in ['C', 'D', 'H', 'S']:
            if self.foundations[suit]:
                foundation_strs.append(str(self.foundations[suit][-1]))
            else:
                foundation_strs.append("--")
        s += f"Foundations: C:{foundation_strs[0]} D:{foundation_strs[1]} H:{foundation_strs[2]} S:{foundation_strs[3]}\n"

        return s

    def apply_move(self, move):
        """
        Copy-on-Write 版本：
        - 仅复制被修改的集合（外层 cascades 列表 + 相关列 / freecells / foundations 某个花色列表）
        - 其他结构共享，避免整状态 deepcopy。
        """
        src_t = move.source_type
        dst_t = move.dest_type
        src_i = move.source_idx
        dst_i = move.dest_idx

        # 起始引用（可能被替换为复制后的）
        cascades = self.cascades
        freecells = self.freecells
        foundations = self.foundations

        cascades_copied = False
        freecells_copied = False
        foundations_copied = False

        # ------ 取出源卡牌 ------
        if src_t == 'cascade':
            # 复制外层列表
            cascades = cascades[:]  # 外层浅拷贝
            cascades_copied = True
            # 复制该列(去掉最后一张)
            source_col_old = self.cascades[src_i]
            card = source_col_old[-1]
            new_source_col = source_col_old[:-1]
            cascades[src_i] = new_source_col
        elif src_t == 'freecell':
            card = freecells[src_i]
            # 复制 freecells 列表
            freecells = freecells[:]
            freecells_copied = True
            freecells[src_i] = None
        else:
            raise ValueError(f"Unsupported source: {src_t}")

        # ------ 放置到目标位置 ------
        if dst_t == 'cascade':
            # 如果外层 cascades 还没复制（源不是 cascade），现在复制
            if not cascades_copied:
                cascades = cascades[:]
                cascades_copied = True
            target_col_old = cascades[dst_i]
            # 复制目标列并 append
            new_target_col = target_col_old + [card]
            cascades[dst_i] = new_target_col

        elif dst_t == 'freecell':
            if not freecells_copied:
                freecells = freecells[:]
                freecells_copied = True
            if freecells[dst_i] is not None:
                raise ValueError("Target freecell not empty")
            freecells[dst_i] = card

        elif dst_t == 'foundation':
            suit = card.suit
            expected_rank = len(foundations[suit]) + 1
            if card.rank != expected_rank:
                raise ValueError(f"Invalid foundation move: expected rank {expected_rank}, got {card.rank}")
            # 复制 foundations dict + 该花色列表
            if not foundations_copied:
                foundations = foundations.copy()
                foundations_copied = True
            new_list = foundations[suit][:]  # 复制当前该花色堆
            new_list.append(card)
            foundations[suit] = new_list
        else:
            raise ValueError(f"Unsupported destination: {dst_t}")

        # 返回新状态（只包含必要复制的容器）
        return State(cascades, freecells, foundations)


class Move:
    def __init__(self, source_type, source_idx, dest_type, dest_idx):
        """
        source_type, dest_type: 'cascade', 'freecell', or 'foundation'
        source_idx, dest_idx: int index of the source/destination
        """
        self.source_type = source_type
        self.source_idx = source_idx
        self.dest_type = dest_type
        self.dest_idx = dest_idx

    def __repr__(self):
        return f"{self.source_type}[{self.source_idx}] → {self.dest_type}[{self.dest_idx}]"


class Card:
    def __init__(self, code):
        self.rank_str = code[:-1]
        self.suit = code[-1]
        self.rank = self.parse_rank(self.rank_str)

    def parse_rank(self, rank_str):
        rank_map = {
            'A': 1, '2': 2, '3': 3, '4': 4, '5': 5,
            '6': 6, '7': 7, '8': 8, '9': 9,
            '10': 10, 'J': 11, 'Q': 12, 'K': 13
        }
        return rank_map[rank_str]

    def color(self):
        return 'black' if self.suit in ['S', 'C'] else 'red'

    def __repr__(self):
        return f"{self.rank_str}{self.suit}"

    def __eq__(self, other):
        return isinstance(other, Card) and self.rank == other.rank and self.suit == other.suit

    def __hash__(self):
        return hash((self.rank, self.suit))


def heuristic_hsdh(state: State):
    """Heineman's Staged Deepening Heuristic (HSDH)"""
    total = 0
    for suit in ['C', 'D', 'H', 'S']:
        foundation = state.foundations[suit]
        next_rank = len(foundation) + 1
        found = False
        for cascade in state.cascades:
            for i, card in enumerate(reversed(cascade)):
                if card.rank == next_rank and card.suit == suit:
                    total += i
                    found = True
                    break
            if found:
                break
    multiplier = 2 if state.freecells.count(None) == 0 or any(len(state.foundations[s]) == 0 for s in ['C', 'D', 'H', 'S']) else 1
    return total * multiplier


def combined_heuristic(state):
    h1 = heuristic_hsdh(state)
    # h2 使用缓存
    h2 = cached_deadlock_heuristic(state)
    h3 = 52 - sum(len(pile) for pile in state.foundations.values())  # 剩余未进 foundation 的牌数
    return h1 + 1000 * h2 + 10 * h3



def is_goal(state: State):
    cascades_empty = all(len(pile) == 0 for pile in state.cascades)
    freecells_empty = all(cell is None for cell in state.freecells)
    return cascades_empty and freecells_empty


def get_legal_moves(state: State):
    moves = []

    # 1. cascade -> cascade
    for i, col in enumerate(state.cascades):
        if not col:
            continue
        top_card = col[-1]
        for j, target_col in enumerate(state.cascades):
            if i == j:
                continue
            if not target_col:
                moves.append(Move("cascade", i, "cascade", j))
            else:
                target_card = target_col[-1]
                if top_card.color() != target_card.color() and top_card.rank == target_card.rank - 1:
                    moves.append(Move("cascade", i, "cascade", j))

    # 2. cascade -> freecell
    for i, col in enumerate(state.cascades):
        if not col:
            continue
        for j, free in enumerate(state.freecells):
            if free is None:
                moves.append(Move("cascade", i, "freecell", j))
                break

    # 3. freecell -> cascade
    for i, card in enumerate(state.freecells):
        if card is None:
            continue
        for j, target_col in enumerate(state.cascades):
            if not target_col:
                moves.append(Move("freecell", i, "cascade", j))
            else:
                top = target_col[-1]
                if card.color() != top.color() and card.rank == top.rank - 1:
                    moves.append(Move("freecell", i, "cascade", j))

    # 4. cascade -> foundation
    for i, col in enumerate(state.cascades):
        if not col:
            continue
        card = col[-1]
        suit = card.suit
        foundation = state.foundations[suit]
        expected_rank = len(foundation) + 1
        if card.rank == expected_rank:
            moves.append(Move("cascade", i, "foundation", 0))  # 目标索引在这里无实际意义

    # 5. freecell -> foundation
    for i, card in enumerate(state.freecells):
        if card is None:
            continue
        suit = card.suit
        foundation = state.foundations[suit]
        expected_rank = len(foundation) + 1
        if card.rank == expected_rank:
            moves.append(Move("freecell", i, "foundation", 0))

    return moves


def state_hash(state: State):
    # （保持原逻辑，仍然会比增量哈希慢，如果后续需要再优化）
    col_tuple = tuple(tuple(str(card) for card in col) for col in state.cascades)
    freecell_tuple = tuple(str(card) if card else None for card in state.freecells)
    foundation_tuple = tuple(
        tuple(str(card) for card in state.foundations[suit]) for suit in ['C', 'D', 'H', 'S']
    )
    return hash((col_tuple, freecell_tuple, foundation_tuple))

# ===== LRU 缓存实现 & 包装 =====
class LRUCache:
    def __init__(self, capacity=200_000):
        self.capacity = capacity
        self._od = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, key):
        if key in self._od:
            self._od.move_to_end(key)
            self.hits += 1
            return self._od[key]
        self.misses += 1
        return None

    def set(self, key, value):
        if key in self._od:
            self._od.move_to_end(key)
        self._od[key] = value
        if len(self._od) > self.capacity:
            self._od.popitem(last=False)

    def stats(self):
        total = self.hits + self.misses
        hit_rate = (self.hits / total) if total else 0.0
        return {
            "size": len(self._od),
            "capacity": self.capacity,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate
        }


def state_struct_key(state: State):
    """
    比 state_hash 更安全的结构键（无碰撞风险，代价仍可接受）。
    结构：
    (
      (('10D','4C',...), ...),                      # cascades
      ('AH','--','...','...'),                      # freecells (None -> '--')
      (('C1','C2',...), ('D1',...), ('H1',...), ('S1',...))  # foundations
    )
    """
    col_tuple = tuple(tuple(str(card) for card in col) for col in state.cascades)
    freecell_tuple = tuple(str(card) if card else '--' for card in state.freecells)
    foundation_tuple = tuple(
        tuple(str(card) for card in state.foundations[suit]) for suit in ['C', 'D', 'H', 'S']
    )
    return (col_tuple, freecell_tuple, foundation_tuple)


# 全局 deadlock LRU
_deadlock_lru = LRUCache(capacity=100_000)  # 容量可按内存调节


def cached_deadlock_heuristic(state: State):
    key = state_struct_key(state)
    val = _deadlock_lru.get(key)
    if val is None:
        val = deadlock_heuristic(state)
        _deadlock_lru.set(key, val)
    return val


def dfs_k_steps(state: State, k: int, trans_table: dict):
    stack = [(state, 0)]
    new_states = []
    local_trans_table = {}

    while stack:
        current_state, depth = stack.pop()

        h = state_hash(current_state)
        if h in local_trans_table:
            continue
        local_trans_table[h] = True

        if is_goal(current_state):
            return [], True, current_state

        if depth == k:
            new_states.append(current_state)
            continue

        legal_moves = get_legal_moves(current_state)
        for move in legal_moves:
            next_state = current_state.apply_move(move)
            stack.append((next_state, depth + 1))

    print(f"[DEBUG] DFS new_states: {len(new_states)}")
    return new_states, False, None


def hsd_solver(initial_state, k, N, timeout=600, progress_hook=None):
    MAX_OPEN_LIST_SIZE = 10000
    transposition_table = {}
    random.seed(42)
    open_list = []
    counter = itertools.count()

    heapq.heappush(open_list, (combined_heuristic(initial_state), next(counter), initial_state))
    
    iterations = 0
    start_time = time.time()

    while open_list:
        if time.time() - start_time > timeout:
            raise TimeoutError(f"搜索超时（>{timeout}秒），未找到解。")

        # 90% 取最优，10% 随机扰动
        if random.random() < 0.9:
            h_val, _, current_state = heapq.heappop(open_list)
        else:
            rand_index = random.randint(0, len(open_list) - 1)
            h_val, _, current_state = open_list[rand_index]
            if rand_index == len(open_list) - 1:
                open_list.pop()
            else:
                open_list[rand_index] = open_list.pop()
                heapq.heapify(open_list)

        print(f"[DEBUG] Heuristic value = {h_val}")

        iterations += 1
        if iterations % 1 == 0:
            print(f"[DEBUG] Iterations: {iterations}, Open list size: {len(open_list)}, Transposition table size: {len(transposition_table)}")

        new_states, found_goal, goal_state = dfs_k_steps(current_state, k, transposition_table)
        if found_goal:
            return goal_state

        for s in new_states:
            if is_goal(s):
                return s
            h_val = combined_heuristic(s)
            h = state_hash(s)
            if h not in transposition_table:
                transposition_table[h] = True
                heapq.heappush(open_list, (h_val, next(counter), s))
                if len(transposition_table) >= N:
                    print(f"[DEBUG] Transposition table reached limit {N}, clearing it")
                    transposition_table.clear()

        if len(open_list) > MAX_OPEN_LIST_SIZE:
            open_list = heapq.nsmallest(MAX_OPEN_LIST_SIZE, open_list)
            heapq.heapify(open_list)

        for _, _, state in open_list:
            if is_goal(state):
                return state

        if progress_hook is not None:
            progress_hook(h_val, iterations)

    return None


if __name__ == "__main__":
    state = State.from_text_block(example)
    print("Initial State:")
    print(state)

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
