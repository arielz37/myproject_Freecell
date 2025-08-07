import os
import time
import matplotlib.pyplot as plt
import traceback
from HSD_3 import State, hsd_solver

# PARAMETER
## 测试的deal数量
TEST_DEAL_NUM = 500

# 读取TestDeals_freecell_32k前10个deal
with open('freecell_32k_deals.txt', 'r') as f:
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

deals = deals[:TEST_DEAL_NUM]
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

    def progress_hook(h_val, iteration):
        heuristics.append(h_val)

    try:
        print(f"开始求解Deal {idx+1}")
        result = hsd_solver(state, k=6, N=100000, timeout=300, progress_hook=progress_hook)
        elapsed = time.time() - start
        all_heuristics.append(heuristics)
        all_times.append(elapsed)
        all_iters.append(len(heuristics))
        # 画启发式变化图
        plt.figure()
        plt.plot(heuristics)
        plt.xlabel('Iteration')
        plt.ylabel('Best Heuristic Value')
        plt.title(f'Deal {idx+1} Heuristic Progress')
        plt.savefig(f'results/deal_{idx+1}_heuristic.png')
        plt.close()
        print(f"Deal {idx+1} finished in {elapsed:.2f}s, {len(heuristics)} iterations.")
    except Exception as e:
        print(f"Deal {idx+1} error or timeout!")
        traceback.print_exc()
        timeout_deals.append(idx+1)
        all_heuristics.append(heuristics)
        all_times.append(600)
        all_iters.append(len(heuristics))

# 画总用时和轮数柱状图
if all_times and all_iters and len(all_times) == TEST_DEAL_NUM and len(all_iters) == TEST_DEAL_NUM:
    plt.figure(figsize=(10,5))
    plt.bar(range(1,TEST_DEAL_NUM+1), all_times)
    plt.xlabel('Deal Number')
    plt.ylabel('Time Used (s)')
    plt.title('Time Used for Each Deal')
    plt.savefig('results/all_deals_time.png')
    plt.close()

    plt.figure(figsize=(10,5))
    plt.bar(range(1,TEST_DEAL_NUM+1), all_iters)
    plt.xlabel('Deal Number')
    plt.ylabel('Iteration Rounds')
    plt.title('Iteration Rounds for Each Deal')
    plt.savefig('results/all_deals_iters.png')
    plt.close()
else:
    print('没有有效的统计数据，无法画图！')

print("\n超时的deal编号:", timeout_deals) 