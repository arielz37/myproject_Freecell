def heuristic_number_well_placed(state: State):
    """统计 cascade 堆中顺序正确且颜色交替的牌数"""
    count = 0
    for pile in state.cascades:
        for i in range(len(pile) - 1):
            top, below = pile[i], pile[i + 1]
            if top.rank == below.rank + 1 and top.color() != below.color():
                count += 1
            else:
                break
    return count


def heuristic_num_cards_not_at_foundations(state: State):
    """统计还未放入 foundation 的牌总数"""
    cascades_total = sum(len(pile) for pile in state.cascades)
    freecells_total = sum(1 for cell in state.freecells if cell is not None)
    return cascades_total + freecells_total


def heuristic_freecells(state: State):
    """统计空闲 FreeCell 和空 cascade 数量"""
    freecell_count = sum(1 for cell in state.freecells if cell is None)
    empty_cascades = sum(1 for pile in state.cascades if len(pile) == 0)
    return freecell_count + empty_cascades


def heuristic_difference_from_top(state: State):
    """cascade 顶牌平均值 - foundation 顶牌平均值"""
    top_cascade = [pile[-1].rank for pile in state.cascades if pile]
    top_foundation = [pile[-1].rank for pile in state.foundations.values() if pile]
    if not top_cascade or not top_foundation:
        return 0
    return sum(top_cascade) / len(top_cascade) - sum(top_foundation) / len(top_foundation)


def heuristic_lowest_home_card(state: State):
    """13 - foundation 中最小的牌值"""
    all_foundation = [pile[-1].rank for pile in state.foundations.values() if pile]
    if not all_foundation:
        return 13
    return 13 - min(all_foundation)


def heuristic_highest_home_card(state: State):
    """foundation 中最大牌值"""
    all_foundation = [pile[-1].rank for pile in state.foundations.values() if pile]
    return max(all_foundation) if all_foundation else 0


def heuristic_difference_home(state: State):
    """foundation 中最大值 - 最小值"""
    all_foundation = [pile[-1].rank for pile in state.foundations.values() if pile]
    return max(all_foundation) - min(all_foundation) if all_foundation else 0


def heuristic_sum_of_bottom_cards(state: State):
    """理论底部最大值（100）- 实际底部牌值总和"""
    actual_sum = sum(pile[0].rank for pile in state.cascades if pile)
    return 100 - actual_sum

