import time
import copy
import heapq

import itertools
from queue import PriorityQueue

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
Deal 3:
  Cascade 1: AD JH QD 9S KD AC 9C
  Cascade 2: 3H JC 6H 5S JS 8S 9H
  Cascade 3: 4C 7H 2C 3S AS 5C QH
  Cascade 4: 7D 7C 6D 2H KC QS 3D
  Cascade 5: 4H QC 6C 4S 2D 2S
  Cascade 6: AH 5D 3C 8D 10H 5H
  Cascade 7: KS 8H 9D 8C 4D KH
  Cascade 8: 10D 10S 6S 10C 7S JD

"""

class State:
    def __init__(self, cascades):
        # cascades: List[List[Card]]
        self.cascades = cascades
        self.freecells = [None] * 4
        self.foundations = {'C': [], 'D': [], 'H': [], 'S': []}

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
        # 深拷贝当前状态
        new_state = copy.deepcopy(self)

        # 获取源位置的卡牌
        if move.source_type == 'cascade':
            card = new_state.cascades[move.source_idx][-1]
            del new_state.cascades[move.source_idx][-1]
        elif move.source_type == 'freecell':
            card = new_state.freecells[move.source_idx]
            new_state.freecells[move.source_idx] = None
        else:
            raise ValueError(f"Unsupported source: {move.source_type}")

        # 放置到目标位置
        if move.dest_type == 'cascade':
            new_state.cascades[move.dest_idx].append(card)
        elif move.dest_type == 'freecell':
            if new_state.freecells[move.dest_idx] is not None:
                raise ValueError("Target freecell not empty")
            new_state.freecells[move.dest_idx] = card
        elif move.dest_type == 'foundation':
            suit = card.suit
            expected_rank = len(new_state.foundations[suit]) + 1
            if card.rank != expected_rank:
                raise ValueError(f"Invalid foundation move: expected rank {expected_rank}, got {card.rank}")
            new_state.foundations[suit].append(card)
        else:
            raise ValueError(f"Unsupported destination: {move.dest_type}")

        return new_state
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

    def __eq__(self, other):
        return (self.source_type == other.source_type and
                self.source_idx == other.source_idx and
                self.dest_type == other.dest_type and
                self.dest_idx == other.dest_idx)

    def __hash__(self):
        return hash((self.source_type, self.source_idx, self.dest_type, self.dest_idx))
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

### Push Github
### Report Google DOC
### EA
### 创建回溯oath方法


### heruistic experiments
def heuristic(current_state):
    return 52-sum(len(pile) for pile in current_state.foundations)


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

### 
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
    # 将状态表示为一个不可变结构用于哈希
    col_tuple = tuple(tuple(str(card) for card in col) for col in state.cascades)
    freecell_tuple = tuple(str(card) if card else None for card in state.freecells)
    foundation_tuple = tuple(
        tuple(str(card) for card in state.foundations[suit]) for suit in ['C', 'D', 'H', 'S']
    )
    return hash((col_tuple, freecell_tuple, foundation_tuple))



def dfs_k_steps(state: State, k: int, initial_g: int, global_trans_table: dict):
    # global_trans_table 是 hsd_solver 的主转置表，只读不写。
    
    # stack: (state, current_g, path_hashes)
    stack = [(state, initial_g, [state_hash(state)])]
    
    # new_end_states: list of (state, final_g)
    new_end_states = []
    
    local_visited_hashes = {state_hash(state)}

    while stack:
        current_state, current_g, path_hashes = stack.pop()
        
        # NOTE: is_goal check in DFS is tricky with g(n), we'll rely on main loop
        if is_goal(current_state):
             return [], True, current_state

        depth = current_g - initial_g
        if depth == k:
            new_end_states.append((current_state, current_g))
            continue

        legal_moves = get_legal_moves(current_state)
        for move in legal_moves:
            next_state = current_state.apply_move(move)
            h_next = state_hash(next_state)

            if h_next not in global_trans_table and h_next not in local_visited_hashes:
                local_visited_hashes.add(h_next)
                stack.append((next_state, current_g + 1, path_hashes + [h_next]))

    print(f"[DEBUG] DFS new_states: {len(new_end_states)}")
    return new_end_states, False, None

def combined_heuristic(state):
    h1 = heuristic_hsdh(state)
    h2 = deadlock_heuristic(state)
    h3 = 52 - sum(len(pile) for pile in state.foundations.values())  # 剩余未进foundation的牌数
    return h1 + 1000 * h2 + 10 * h3

def hsd_solver(initial_state, k, N, timeout=600, progress_hook=None):
    import itertools
    import time
    MAX_OPEN_LIST_SIZE = 10000  
    
    # transposition_table: hash -> best_g_so_far
    transposition_table = {}
    
    # open_list: (f_val, tie_breaker, g_val, state)
    open_list = []
    counter = itertools.count()
    
    # --- Initial State Handling ---
    initial_g = 0
    initial_h = combined_heuristic(initial_state)
    initial_f = initial_g + initial_h
    initial_hash = state_hash(initial_state)
    
    heapq.heappush(open_list, (initial_f, next(counter), initial_g, initial_state))
    transposition_table[initial_hash] = initial_g

    iterations = 0
    start_time = time.time()

    while open_list:
        if time.time() - start_time > timeout:
            raise TimeoutError(f"搜索超时（>{timeout}秒），未找到解。")

        f_val, _, g_val, current_state = heapq.heappop(open_list)

        # A* check: if we found a shorter path to an already popped state, ignore this one
        current_hash = state_hash(current_state)
        if g_val > transposition_table.get(current_hash, float('inf')):
             continue

        print(f"[DEBUG] Popped f={f_val} (g={g_val}, h={f_val - g_val})")
        if iterations % 10 == 0:
            print(f"[DEBUG] Iterations: {iterations}, Open list size: {len(open_list)}, Transposition table size: {len(transposition_table)}")
        iterations += 1
        
        # --- DFS Step ---
        # Pass the current g_val
        new_states_with_g, found_goal, goal_state = dfs_k_steps(current_state, k, g_val, transposition_table)
        
        if found_goal:
            return goal_state

        for s, new_g in new_states_with_g:
            if is_goal(s):
                return s
            
            s_hash = state_hash(s)

            # A* Core Logic
            if new_g < transposition_table.get(s_hash, float('inf')):
                transposition_table[s_hash] = new_g
                h_s = combined_heuristic(s)
                f_s = new_g + h_s
                heapq.heappush(open_list, (f_s, next(counter), new_g, s))
        
        # 清空逻辑可以恢复，但仍然有风险。如果内存允许，建议注释掉。
        if len(transposition_table) >= N:
            print(f"[DEBUG] Transposition table reached limit {N}, clearing it. (This can be risky)")
            transposition_table.clear()

        if len(open_list) > MAX_OPEN_LIST_SIZE:
            open_list = heapq.nsmallest(MAX_OPEN_LIST_SIZE, open_list)
            heapq.heapify(open_list)

        # for _, _, state in open_list:
        #     if is_goal(state):
        #         return state

        if progress_hook is not None:
            progress_hook(f_val, iterations)

    return None


if __name__ == "__main__":
    state = State.from_text_block(example)
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

