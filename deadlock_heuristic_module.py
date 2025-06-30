from collections import defaultdict

"""
Module: deadlock_heuristic_module
Provides a deadlock detection heuristic for FreeCell search algorithms.
Functions:
- build_dependency_graph(state)
- find_cycles(graph, nodes, max_length=3)
- greedy_minimum_hitting_set(cycles)
- deadlock_heuristic(state)
"""

def build_dependency_graph(state):
    """
    Build a dependency graph for cards in a given FreeCell state.
    Nodes are Card objects not yet in foundations.
    Edges:
      - blocking edges: c -> c' if c is under c' in a cascade pile
      - foundation edges: c -> c' if same suit and c.rank > c'.rank
    Returns:
      graph: dict(Card -> set(Card))
      nodes: list of all Card nodes
    """
    graph = defaultdict(set)

    # Blocking edges
    for pile in state.cascades:
        for i in range(len(pile) - 1):
            under = pile[i]
            above = pile[i + 1]
            graph[under].add(above)

    # Foundation edges
    for suit in state.foundations:
        # Collect all cards of this suit in cascades
        cards = []
        for pile in state.cascades:
            cards.extend([card for card in pile if card.suit == suit])
        # Sort by rank to connect each higher rank to all lower ranks
        cards_sorted = sorted(cards, key=lambda c: c.rank)
        for i in range(1, len(cards_sorted)):
            higher = cards_sorted[i]
            for j in range(i):
                lower = cards_sorted[j]
                if higher.rank > lower.rank:
                    graph[higher].add(lower)

    # Gather all nodes
    nodes = set(graph.keys())
    for targets in graph.values():
        nodes.update(targets)

    return graph, list(nodes)


def find_cycles(graph, nodes, max_length=3):
    """
    Find all simple cycles up to a given max_length in the directed graph.
    Returns a list of sets, each set is the nodes in one cycle.
    """
    cycles = []

    def dfs(path, visited):
        current = path[-1]
        for neighbor in graph.get(current, []):
            if neighbor in path:
                idx = path.index(neighbor)
                cycle = path[idx:]
                if 1 < len(cycle) <= max_length:
                    cycles.append(set(cycle))
                continue
            if neighbor not in visited and len(path) < max_length:
                dfs(path + [neighbor], visited | {neighbor})

    for node in nodes:
        dfs([node], {node})

    return cycles


def greedy_minimum_hitting_set(cycles):
    """
    Approximate a minimum hitting set for the collection of cycles using a greedy heuristic.
    Returns a set of Card nodes hitting all cycles.
    """
    hitting_set = set()
    uncovered = set(range(len(cycles)))

    while uncovered:
        counts = defaultdict(int)
        for idx in uncovered:
            for card in cycles[idx]:
                counts[card] += 1
        if not counts:
            break
        # Select the card that covers the most cycles
        best_card = max(counts, key=counts.get)
        hitting_set.add(best_card)
        # Remove covered cycles
        covered = {idx for idx in uncovered if best_card in cycles[idx]}
        uncovered -= covered

    return hitting_set


def deadlock_heuristic(state):
    """
    Compute the deadlock heuristic value for a FreeCell state.
    Returns the size of a greedy minimum hitting set for dependency cycles.
    """
    graph, nodes = build_dependency_graph(state)
    cycles = find_cycles(graph, nodes)
    if not cycles:
        return 0
    hitting_set = greedy_minimum_hitting_set(cycles)
    return len(hitting_set)
