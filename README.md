# FreeCell AI Solver

This is a heuristic search-based FreeCell card game AI solver project. The project implements efficient FreeCell game state representation, deadlock detection algorithms, and heuristic search solvers.

## Project Overview

This project contains the following core functionalities:
- **HSD (Heuristic Search with Deadlock detection)** algorithm implementation
- **Deadlock heuristic detection** module
- **Graphical solver interface**
- **Batch testing and performance analysis** tools

## Project Structure

### Core Algorithm Files

#### `HSD_3.py` - Main Algorithm Implementation
This is the core file of the project, containing the complete FreeCell solving algorithm:

- **State class**: Game state representation, including cascades, freecells, and foundations
- **Card class**: Playing card object, supporting suit and rank representation
- **Move class**: Move operation representation
- **hsd_solver()**: Main heuristic search solver
- **heuristic_hsdh()**: Heuristic function implementation
- **deadlock_heuristic()**: Deadlock detection heuristic

**Algorithm Features:**
- Uses heuristic search (A* variant)
- Integrates deadlock detection to avoid invalid searches
- Supports k-step depth search
- Has timeout control and progress callbacks

#### `deadlock_heuristic_module.py` - Deadlock Detection Module
High-speed deadlock heuristic detection implementation:
- Detects circular dependencies in the game
- Calculates minimum hitting-set size
- Compatible with both int and Card state representations
- Single call takes approximately 0.2-0.4ms

### Interface and Utility Files

#### `solver.py` - Graphical Solver Interface
Simple graphical interface based on tkinter:
- Text input area for entering game layout
- One-click solve functionality
- Result display area
- Error handling and user prompts

**Launch method:**
```bash
python solver.py
```

#### `batch_test.py` - Batch Testing Tool
Used for large-scale testing and performance analysis:
- Reads test cases from `freecell_32k_deals.txt`
- Runs solver in batch mode
- Generates performance statistics charts
- Saves heuristic progression curves

#### `heuristic_sets.py` - Heuristic Function Collection
Contains implementations of various heuristic functions:
- `heuristic_number_well_placed()`: Counts correctly arranged cards
- `heuristic_num_cards_not_at_foundations()`: Counts cards not yet placed in foundations
- `heuristic_freecells()`: Counts available spaces
- `heuristic_difference_from_top()`: Calculates top card value differences
- And many other heuristic functions

### Data Files

#### `freecell_32k_deals.txt` - Test Case Data
Contains 32,000 FreeCell game layout test cases for algorithm validation and performance testing.

### Result Files

#### `results/` Directory
Contains test results and charts:
- `deal_*_heuristic.png`: Individual game heuristic progression curves
- `all_deals_time.png`: Solving time statistics for all games
- `all_deals_iters.png`: Iteration count statistics for all games

##  Quick Start

### Environment Requirements
```bash
pip install -r requirements.txt
```

### Launch Graphical Interface
```bash
python solver.py
```

### Input Format Example
```
Deal 1:
  Cascade 1: JS 10H 9S KD 5D AD 5C
  Cascade 2: 10C 6C 9D AH 6S QD 10S
  Cascade 3: QH 4H 2S 9H AC 3S JH
  Cascade 4: 10D KS AS JC 2H 5H 9C
  Cascade 5: 3C 5S KC 8H 4S 3H
  Cascade 6: KH 3D QS 4C 2C 6H
  Cascade 7: 7D JD 7H 6D 7S 8C
  Cascade 8: QC 8S 8D 2D 7C 4D
```

### Result Display
```
Solution:
cascade[5] → freecell[0]
cascade[2] → freecell[1]
cascade[2] → freecell[2]
cascade[2] → foundation[0]
cascade[0] → freecell[3]
cascade[0] → foundation[0]
cascade[5] → foundation[0]
...
```


## Algorithm Details

### HSD Algorithm Core Concepts

1. **Heuristic Search**: Uses A* algorithm variant combined with multiple heuristic functions
2. **Deadlock Detection**: Detects circular dependencies in the game through graph theory methods
3. **k-step Search**: Supports multi-step depth search to improve solving efficiency
4. **State Caching**: Uses LRU cache to avoid redundant calculations

### Main Heuristic Functions

- **HSDH**: Comprehensive heuristic combining multiple metrics
- **Deadlock Heuristic**: Detects game deadlock states
- **Position Heuristic**: Evaluates card arrangement quality
- **Space Heuristic**: Evaluates available space

##  Performance Characteristics

- **Solving Speed**: Most games can be solved within 50 seconds
- **Success Rate**: Achieves high success rate on test sets
- **Memory Usage**: Optimized state representation and caching mechanisms
- **Scalability**: Supports different parameter configurations and heuristic combinations

##  Development Guide

### Modifying Algorithm Parameters
Adjust the following parameters in `HSD_3.py`:
- `k`: k-step search depth
- `N`: Maximum iteration count
- `timeout`: Timeout duration
- `randomRate`: Randomization ratio

### Custom Testing
Modify the `TEST_DEAL_NUM` parameter in `batch_test.py` to adjust test scale.

##  Important Notes

1. Ensure correct input format, strictly follow the example format
2. Complex games may require longer solving time
3. Deadlock detection module has significant impact on performance
4. Recommend backing up important data before testing