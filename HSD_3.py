import time
import heapq
import itertools
import random
from collections import OrderedDict

from deadlock_heuristic_module import deadlock_heuristic

# Global Parameter
randomRate = 0.80

# Simple example
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
# Standard Example
example = """
Deal 1:
  Cascade 1: JS 10H 9S KD 5D AD 5C
  Cascade 2: 10C 6C 9D AH 6S QD 10S
  Cascade 3: QH 4H 2S 9H AC 3S JH
  Cascade 4: 10D KS AS JC 2H 5H 9C
  Cascade 5: 3C 5S KC 8H 4S 3H
  Cascade 6: KH 3D QS 4C 2C 6H
  Cascade 7: 7D JD 7H 6D 7S 8C
  Cascade 8: QC 8S 8D 2D 7C 4D
"""

class State:
    """
    Represents a complete configuration of a FreeCell game state, including cascades, freecells, and foundations.

    Attributes:
        cascades (List[List[Card]]): A list of 8 cascade piles, each holding a stack of cards.
        freecells (List[Optional[Card]]): A list of 4 freecells, each of which can hold one card or be empty.
        foundations (Dict[str, List[Card]]): A dictionary mapping each suit ('C', 'D', 'H', 'S') to a list of cards placed in ascending order.

    Methods:
        from_text_block(text_block):
            Static method to create a State object from a textual representation of the initial game layout.
        
        __repr__():
            Returns a formatted string representation of the state, including all cascades, freecells, and foundations.
        
        apply_move(move):
            Returns a new State object resulting from applying the given move. The method handles updating the appropriate 
            source and destination containers (cascade, freecell, or foundation) and performs shallow copying to ensure 
            immutability of the original state.

    Purpose:
        Used to model the current configuration of a FreeCell game in a solver or search algorithm. The class supports
        state transitions and printing, and is designed to be used in heuristic search and planning-based solving approaches.
    """

    def __init__(self, cascades, freecells=None, foundations=None):
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

        src_t = move.source_type
        dst_t = move.dest_type
        src_i = move.source_idx
        dst_i = move.dest_idx

        cascades = self.cascades
        freecells = self.freecells
        foundations = self.foundations

        cascades_copied = False
        freecells_copied = False
        foundations_copied = False

        # ------ Remove source card ------
        if src_t == 'cascade':

            cascades = cascades[:]  # Outer shallow copy
            cascades_copied = True

            source_col_old = self.cascades[src_i]
            card = source_col_old[-1]
            new_source_col = source_col_old[:-1]
            cascades[src_i] = new_source_col
        elif src_t == 'freecell':
            card = freecells[src_i]
            # Copy the freecells list
            freecells = freecells[:]
            freecells_copied = True
            freecells[src_i] = None
        else:
            raise ValueError(f"Unsupported source: {src_t}")

        # ------ Place it at the target position ------
        if dst_t == 'cascade':
            if not cascades_copied:
                cascades = cascades[:]
                cascades_copied = True
            target_col_old = cascades[dst_i]
            
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
            
            if not foundations_copied:
                foundations = foundations.copy()
                foundations_copied = True
            new_list = foundations[suit][:]
            new_list.append(card)
            foundations[suit] = new_list
        else:
            raise ValueError(f"Unsupported destination: {dst_t}")

        # Return to a new state (only for containers that need to be copied)
        return State(cascades, freecells, foundations)


class Move:
    """
    Represents a move in the FreeCell game, specifying the source and destination of a card movement.

    Attributes:
        source_type (str): The type of the source ('cascade', 'freecell', or 'foundation').
        source_idx (int): The index of the source pile or cell.
        dest_type (str): The type of the destination ('cascade', 'freecell', or 'foundation').
        dest_idx (int): The index of the destination pile or cell.

    Methods:
        __init__(source_type, source_idx, dest_type, dest_idx):
            Initializes a Move object with the specified source and destination.
        __repr__():
            Returns a string representation of the move.

    Purpose:
        Used to represent a single legal move in the FreeCell solver, allowing the solver to apply and track moves between states.
    """
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
    """
    Represents a single playing card in the FreeCell game.

    Attributes:
        rank_str (str): The string representation of the card's rank (e.g., 'A', '2', ..., '10', 'J', 'Q', 'K').
        suit (str): The suit of the card ('C', 'D', 'H', 'S').
        rank (int): The integer value of the card's rank (Ace=1, ..., King=13).

    Methods:
        __init__(code):
            Initializes a Card object from a string code (e.g., 'AS', '10D').
        parse_rank(rank_str):
            Converts a rank string to its integer value.
        color():
            Returns the color of the card ('red' or 'black').
        __repr__():
            Returns a string representation of the card.
        __eq__(other):
            Checks equality with another Card object.
        __hash__():
            Returns a hash value for the card.

    Purpose:
        Used to model individual cards in the FreeCell game, supporting comparison, hashing, and color determination for move legality.
    """
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
    """
    Combined heuristic function for FreeCell solver.

    This function aggregates three different heuristics:
    - h1: Heineman's Staged Deepening Heuristic (HSDH), which estimates the effort to move cards to foundations based on their positions in cascades.
    - h2: Deadlock heuristic (cached), which detects and penalizes deadlocked or nearly deadlocked states using domain-specific logic.
    - h3: The number of cards not yet in the foundations (i.e., 52 minus the total number of cards in all foundations), representing remaining progress.

    The final heuristic value is a weighted sum: h1 + 1000 * h2 + 10 * h3.
    """
    h1 = heuristic_hsdh(state)
    h2 = cached_deadlock_heuristic(state)
    h3 = 52 - sum(len(pile) for pile in state.foundations.values())  # The remaining number of cards that have not entered foundation
    return h1 + 1000 * h2 + 10 * h3


def is_goal(state: State):
    """
    Checks if the current state is a goal state in the FreeCell game.

    A goal state is defined as a state where all cascades are empty and all freecells are empty.
    """
    cascades_empty = all(len(pile) == 0 for pile in state.cascades)
    freecells_empty = all(cell is None for cell in state.freecells)
    return cascades_empty and freecells_empty


def get_legal_moves(state: State):
    """
    Generates all legal moves for a given state in the FreeCell game.

    This function iterates through all possible moves and checks if they are legal according to the rules of FreeCell.
    It returns a list of Move objects representing all valid moves.
    """
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
    # (keep the original logic, it will still be slower than incremental hashing, if needed, optimize later)
    col_tuple = tuple(tuple(str(card) for card in col) for col in state.cascades)
    freecell_tuple = tuple(str(card) if card else None for card in state.freecells)
    foundation_tuple = tuple(
        tuple(str(card) for card in state.foundations[suit]) for suit in ['C', 'D', 'H', 'S']
    )
    return hash((col_tuple, freecell_tuple, foundation_tuple))

# ===== LRU cache implementation & wrapper =====
class LRUCache:
    """
    Least Recently Used (LRU) cache implementation.
    """

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

    col_tuple = tuple(tuple(str(card) for card in col) for col in state.cascades)
    freecell_tuple = tuple(str(card) if card else '--' for card in state.freecells)
    foundation_tuple = tuple(
        tuple(str(card) for card in state.foundations[suit]) for suit in ['C', 'D', 'H', 'S']
    )
    return (col_tuple, freecell_tuple, foundation_tuple)


# Global deadlock LRU
_INT_LRU = LRUCache(capacity=500_000)      # 50 万条

def cached_deadlock_heuristic(state: State) -> int:
    """
    带全局 LRU 的 deadlock_heuristic 包装器。
    仅当满足“空 freecell ≤2 且 Foundation ≥15 张”才真正调用 deadlock_heuristic，
    否则直接返回 0，避免浪费。
    """
    free_empty = state.freecells.count(None)
    done = sum(len(p) for p in state.foundations.values())
    # if free_empty > 3 or done < 15:
    #     return 0      # 早期/宽松阶段无需检测死锁

    key = state_struct_key(state)
    val = _INT_LRU.get(key)
    if val is None:
        val = deadlock_heuristic(state)
        _INT_LRU.set(key, val)
    return val


# ===== Main Solver =====
# ===== First-Layer=====
# Depth-First Search (DFS) 
def dfs_k_steps(state: State, k: int, trans_table: dict, path_prefix: list):
    """
    Performs a depth-limited depth-first search (DFS) from the given state up to k steps.

    This function explores all possible states reachable from the initial state within k moves, using DFS. 
    It avoids revisiting states within the current DFS tree by maintaining a local transposition table. 
    If a goal state is found during the search, it returns immediately. Otherwise, it collects all unique states reached at exactly depth k and returns them for further exploration by higher-level search algorithms (e.g., staged deepening or A* variants).

    Args:
        state (State): The starting state for DFS.
        k (int): The maximum depth to search.
        trans_table (dict): A (global) transposition table for duplicate detection (not modified here).
        current_path (list): The path from initial state to current state.

    Returns:
        new_states (list): List of tuples (state, complete_moves_to_reach_state) for states reached at depth k.
        found_goal (bool): True if a goal state was found during DFS, else False.
        goal_state (tuple or None): (goal_state, complete_moves_to_goal) if found, else None.
    """
    stack = [(state, 0, [])]          # (state, depth, moves_from_start)
    local_seen, local_dl = set(), {}  # 本轮去重 / 死锁缓存
    frontier = []

    while stack:
        st, depth, moves = stack.pop()
        h = state_hash(st)
        if h in local_seen:
            continue
        local_seen.add(h)

        # 记录 / 复用 deadlock 值（供调用者调试时查看）
        if h not in local_dl:
            local_dl[h] = cached_deadlock_heuristic(st)

        if is_goal(st):
            return [], True, (st, path_prefix + moves)

        if depth == k:
            frontier.append((st, path_prefix + moves))
            continue

        for mv in get_legal_moves(st):
            nxt = st.apply_move(mv)
            stack.append((nxt, depth + 1, moves + [mv]))

    return frontier, False, None

# ===== Second-Layer=====
# Heuristic Search and Planning-Based Solving
def hsd_solver(initial_state, k, N, timeout=600, progress_hook=None):
    """
    Heuristic Search and Planning-Based Solver for FreeCell (HSD algorithm).

    This function implements a staged deepening heuristic search for solving FreeCell. 
    It uses a best-first search (with a weighted heuristic) combined with periodic random exploration to avoid local minima. 
    At each iteration, it expands the most promising state (or a random one with some probability), and for each, performs a depth-limited DFS (see dfs_k_steps) to generate new states. 
    Duplicate states are filtered using a transposition table. The search continues until a goal state is found, the open list is exhausted, or a timeout occurs.

    Args:
        initial_state (State): The starting state of the FreeCell game.
        k (int): The depth limit for each DFS expansion.
        N (int): The maximum size of the transposition table before clearing.
        timeout (float): Maximum allowed time (in seconds) for the search.
        progress_hook (callable, optional): Function called with (h_val, iterations) for progress reporting.

    Returns:
        tuple: (final_state, solution_path) where final_state is the solved goal state (or None if not found) and solution_path is a list of Move objects representing the solution sequence.
    """
    MAX_OPEN_LIST_SIZE = 10000
    transposition_table = {}
    random.seed(42)
    open_list = []
    counter = itertools.count()

    # Track solution path: each state in open_list will have its path
    state_paths = {state_hash(initial_state): []}  # Map state hash to path to reach it
    
    heapq.heappush(open_list, (combined_heuristic(initial_state), next(counter), initial_state))
    
    iterations = 0
    start_time = time.time()

    while open_list:
        if time.time() - start_time > timeout:
            raise TimeoutError(f"搜索超时Timeout（>{timeout}秒），未找到解。")

        # 90% 取最优，10% 随机扰动
        if random.random() < randomRate:
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

        current_path = state_paths[state_hash(current_state)]
        new_states, found_goal, goal_state = dfs_k_steps(current_state, k, transposition_table, current_path)
        
        if found_goal and goal_state is not None:
            goal_state_obj, complete_path = goal_state
            return goal_state_obj, complete_path

        for s, complete_path in new_states:
            if is_goal(s):
                return s, complete_path
            h_val = combined_heuristic(s)
            h = state_hash(s)
            if h not in transposition_table:
                transposition_table[h] = True
                # The complete_path is already the full path from initial state
                state_paths[h] = complete_path
                heapq.heappush(open_list, (h_val, next(counter), s))
                if len(transposition_table) >= N:
                    print(f"[DEBUG] Transposition table reached limit {N}, clearing it")
                    transposition_table.clear()

        if len(open_list) > MAX_OPEN_LIST_SIZE:
            open_list = heapq.nsmallest(MAX_OPEN_LIST_SIZE, open_list)
            heapq.heapify(open_list)

        for _, _, state in open_list:
            if is_goal(state):
                return state, state_paths[state_hash(state)]
            
        if progress_hook is not None:
            progress_hook(h_val, iterations)

    return None, []

# ===== Main Function =====
if __name__ == "__main__":
    state = State.from_text_block(example)
    print("Initial State:")
    print(state)

    k = 6
    N = 100000

    start = time.time()
    print("Solving...")
    try:
        result, solution_path = hsd_solver(state, k, N, timeout=600)
    except TimeoutError as e:
        print(str(e))
        result = None
        solution_path = []

    print("Time:", time.time() - start)

    if result:
        print("Solved! Final State:")
        print(result)
        print("Solution Path:")
        for move in solution_path:
            print(move)
    else:
        print("No solution found.")