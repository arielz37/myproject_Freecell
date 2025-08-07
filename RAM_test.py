import tracemalloc, psutil, os, time
from HSD_3 import State, hsd_solver

# Standard Example
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

tracemalloc.start()
state = State.from_text_block(example)
hsd_solver(state, k=6, N=100000, timeout=600)                     
print(tracemalloc.get_traced_memory())   # (current, peak)
print('RSS:', psutil.Process(os.getpid()).memory_info().rss // 1024**2, 'MB')
