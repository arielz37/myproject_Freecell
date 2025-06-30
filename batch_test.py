import os
import time
import matplotlib.pyplot as plt
import traceback
from HSD import State, hsd_solver, combined_heuristic, dfs_k_steps, is_goal, state_hash

# 读取TestDeals_freecell_32k前10个deal
with open('TestDeals_freecell_32k', 'r') as f:
    lines = f.readlines()

deals = []
deal = []
for line in lines:
    if line.startswith('Deal') and deal:
        deals.append(''.join(deal))
        deal = [line]
    else:
        deal.append(line)
if deal:
    deals.append(''.join(deal))

deals = deals[:10]
print(f"共{len(deals)}个deal")

# 结果保存目录
os.makedirs('results', exist_ok=True)

# 记录结果
all_heuristics = []
all_times = []
all_iters = []
timeout_deals = []

for idx, deal_text in enumerate(deals):
    print(f"\n===== Testing Deal {idx+1} =====")
    print(f"Deal {idx+1}内容：\n{deal_text}")
    try:
        state = State.from_text_block(deal_text)
        print(f"Deal {idx+1} State对象：\n{state}")
    except Exception as e:
        print(f"Deal {idx+1} State.from_text_block失败！")
        traceback.print_exc()
        timeout_deals.append(idx+1)
        all_heuristics.append([])
        all_times.append(0)
        all_iters.append(0)
        continue
    heuristics = []
    start = time.time()
    timeout_flag = False
    
    def progress_hook(h_val):
        heuristics.append(h_val)

    # 包装hsd_solver，记录每轮最优heuristic value
    def hsd_solver_with_hook(state, k, N, timeout=600):
        import itertools
        import heapq
        MAX_OPEN_LIST_SIZE = 10000
        transposition_table = {}
        open_list = []
        counter = itertools.count()
        heapq.heappush(open_list, (combined_heuristic(state), next(counter), state))
        iterations = 0
        start_time = time.time()
        best_h_val = float('inf')
        while open_list:
            if time.time() - start_time > timeout:
                print(f"Deal {idx+1} 超时退出")
                raise TimeoutError(f"Timeout >{timeout}s")
            h_val, _, current_state = heapq.heappop(open_list)
            iterations += 1
            if h_val < best_h_val:
                best_h_val = h_val
                progress_hook(best_h_val)
            if iterations % 100 == 0:
                print(f"Deal {idx+1} 迭代{iterations}，当前最优启发式值：{best_h_val}")
            new_states, found_goal, goal_state = dfs_k_steps(current_state, 6, transposition_table)
            if found_goal:
                print(f"Deal {idx+1} 找到goal，迭代{iterations}")
                return goal_state, iterations
            for s in new_states:
                if is_goal(s):
                    print(f"Deal {idx+1} 找到goal，迭代{iterations}")
                    return s, iterations
                h_val = combined_heuristic(s)
                h = state_hash(s)
                if h not in transposition_table:
                    transposition_table[h] = True
                    heapq.heappush(open_list, (h_val, next(counter), s))
                    if len(transposition_table) >= 100000:
                        transposition_table.clear()
            if len(open_list) > MAX_OPEN_LIST_SIZE:
                open_list = heapq.nsmallest(MAX_OPEN_LIST_SIZE, open_list)
                heapq.heapify(open_list)
        print(f"Deal {idx+1} open_list为空，未找到解")
        return None, iterations

    try:
        print(f"开始求解Deal {idx+1}")
        result, iters = hsd_solver_with_hook(state, k=6, N=100000, timeout=600)
        elapsed = time.time() - start
        all_heuristics.append(heuristics)
        all_times.append(elapsed)
        all_iters.append(iters)
        # 画启发式变化图
        plt.figure()
        plt.plot(heuristics)
        plt.xlabel('Iteration')
        plt.ylabel('Best Heuristic Value')
        plt.title(f'Deal {idx+1} Heuristic Progress')
        plt.savefig(f'results/deal_{idx+1}_heuristic.png')
        plt.close()
        print(f"Deal {idx+1} finished in {elapsed:.2f}s, {iters} iterations.")
    except Exception as e:
        print(f"Deal {idx+1} error or timeout!")
        traceback.print_exc()
        timeout_deals.append(idx+1)
        all_heuristics.append(heuristics)
        all_times.append(600)
        all_iters.append(len(heuristics))

# 画总用时和轮数柱状图
if all_times and all_iters and len(all_times) == 10 and len(all_iters) == 10:
    plt.figure(figsize=(10,5))
    plt.bar(range(1,11), all_times)
    plt.xlabel('Deal Number')
    plt.ylabel('Time Used (s)')
    plt.title('Time Used for Each Deal')
    plt.savefig('results/all_deals_time.png')
    plt.close()

    plt.figure(figsize=(10,5))
    plt.bar(range(1,11), all_iters)
    plt.xlabel('Deal Number')
    plt.ylabel('Iteration Rounds')
    plt.title('Iteration Rounds for Each Deal')
    plt.savefig('results/all_deals_iters.png')
    plt.close()
else:
    print('没有有效的统计数据，无法画图！')

print("\n超时的deal编号:", timeout_deals) 