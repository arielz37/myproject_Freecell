# deadlock_heuristic_module.py
# ---------------------------------------------
# High-speed FreeCell deadlock heuristic (compatible with int / Card state representations)
# Python ≥3.8 pure implementation, single call ≈0.2-0.4 ms
# ---------------------------------------------

from typing import List, Set, Tuple

# ────────── Internal constants and tables ──────────
SUIT_TO_ID = {'C': 0, 'D': 1, 'H': 2, 'S': 3}
_ID_RANK:  list[int] = [cid // 4 + 1 for cid in range(52)]
_ID_SUIT:  list[int] = [cid & 3        for cid in range(52)]

# ────────── Helper: Convert Card objects → int card_id ──────────
def _cards_to_ids(card_list):
    """Convert Card object list or int list to unified card_id(int) list"""
    if not card_list:
        return []
    # If already int
    if isinstance(card_list[0], int):
        return list(card_list)
    # Otherwise assume Card objects
    ids = []
    for c in card_list:
        suit_id = SUIT_TO_ID[c.suit]
        cid = (c.rank - 1) * 4 + suit_id
        ids.append(cid)
    return ids

def _extract_int_cascades(state) -> List[List[int]]:
    """
    Compatible with:
      state.cascades == List[List[int]]              (recommended)
      state.cascades == List[List[Card]]
    """
    int_casc = []
    for pile in state.cascades:
        int_casc.append(_cards_to_ids(pile))
    return int_casc

# ────────── Core deadlock heuristic implementation ──────────
def _deadlock_fast(cascades: List[List[int]]) -> int:
    """Core algorithm: int cascades → hitting-set size"""
    edges: list[Set[int]] = [set() for _ in range(52)]
    nodes: Set[int] = set()

    # 1) Blocking edges: adjacent in same column
    for col in cascades:
        for a, b in zip(col, col[1:]):
            edges[a].add(b)
            nodes.update((a, b))

    # 2) Foundation dependencies: same suit rank → rank-1
    for col in cascades:
        for cid in col:
            r = _ID_RANK[cid]
            if r > 1:
                below = (r - 2) * 4 + _ID_SUIT[cid]
                edges[cid].add(below)
                nodes.update((cid, below))

    # 3) Enumerate cycles ≤3 length
    cycles: list[Set[int]] = []
    for u in nodes:
        for v in edges[u]:
            if u in edges[v]:              # length-2 cycle
                cycles.append({u, v})
            for w in edges[v]:             # length-3 cycle
                if u in edges[w]:
                    cycles.append({u, v, w})

    if not cycles:
        return 0

    # 4) Greedy hitting set
    uncovered = cycles[:]          # remaining uncovered cycles
    hitting: Set[int] = set()
    while uncovered:
        counts: dict[int, int] = {}
        for cyc in uncovered:
            for c in cyc:
                counts[c] = counts.get(c, 0) + 1
        if not counts:             # theoretically shouldn't happen
            break
        # Select card with most occurrences
        best = max(counts.items(), key=lambda it: it[1])[0]
        hitting.add(best)
        # Remove covered cycles
        uncovered = [cyc for cyc in uncovered if best not in cyc]

    return len(hitting)

# ────────── External main function ──────────
def deadlock_heuristic(state) -> int:
    """
    External call interface.
    Compatible with:
        - state.cascades as List[List[int]], each card is 0-51
        - or Card objects (must have .rank .suit)
    Returns: greedy hitting-set size (integer), larger value = closer to deadlock
    """
    int_cascades = _extract_int_cascades(state)
    return _deadlock_fast(int_cascades)

__all__ = ["deadlock_heuristic"]
