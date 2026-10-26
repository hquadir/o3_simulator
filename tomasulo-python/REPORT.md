# Programming Assignment Report: Multiple-Issue Tomasulo Algorithm

## 1. Introduction
We use Tomasulo's algorithm for dynamic out-of-order scheduling of instructions, enabling register renaming via a Register Alias Table (RAT), speculative execution, and in-order commitment using a Reorder Buffer (ROB).

In this assignment, we modify the baseline single-issue Python implementation of the Tomasulo algorithm to support:
1. Issuing multiple instructions per clock cycle (`Issue width = 1` to `4`), writing back multiple completed instructions on the Common Data Bus (CDB), and committing multiple instructions per cycle in program order.
2. Configurable hardware parameters (such as number of reservation stations, execution latencies, number of functional units, ROB size, and issue width) which are parsed directly from the test case files.

### What Works
- **Multiple Issue, Write-Back, and Commit:** This supports configurable issue widths from 1 to 4 instructions per cycle.
- **Pipelined & Multi-Unit Functional Units:** This supports pipelined functional units and configurations with multiple functional units (`# of FUs > 1`).
- **In-Order Dispatch & Dependency Enforcement:** For ready instructions in reservation stations that are dispatched in program (issue) order while respecting true data dependencies, WAW/WAR register renaming, and store-to-load forwarding.

### Limitations
- **Branch Prediction on Multi-Issue:** When branch instructions (`Bne`/`Beq`) are issued, instruction fetching stalls (`PC.valid = 0`) until the branch is resolved in the EX stage.
- **Non-Pipelined Memory Unit:** The data memory unit (`ld_sd_mem`) is single-ported and non-pipelined.

---

## 2. Code Changes

1. **`issue.py` (Multi-Instruction Issue):**
   - Here we added `issue_width` to `issue()` and wrapped instruction fetch/decode in a loop `for _ in range(min(issue_width, len(instructions) - PC.PC)):`.
   - Up to `issue_width` instructions are fetched, allocated in the ROB and Reservation Stations / Load-Store Queue, and renamed in the RAT per cycle until a structural hazard or control instruction (`Bne`/`Beq`) is encountered.

2. **`wb.py` (Multi-Instruction Write-Back & WAW Guard):**
   - Here we added `issue_width` to `wb()` so up to `issue_width` completed instructions in `results_buffer` can broadcast on the CDB in a single clock cycle.
   - Here we added a tag check in `boroadcast()` (`if rat_fp[reg_num] == dest_tag:`) so an older instruction's broadcast only updates the RAT entry if a newer instruction has not already renamed that architectural register.

3. **`commit.py` (Multi-Instruction Commit):**
   - Here we added `issue_width` to `commit()` to pop and commit up to `issue_width` ready instructions from the head of the ROB per cycle in strict program order.

4. **`exe.py`, `mem.py`, and `main.py` (Multi-FU Execution & Stage Ordering):**
   - Here we added `cycle_call_history` in `exe.py` to prevent functional unit entries from being incremented twice in the same cycle.
   - Here we updated `check_valid_ins_in_rs()` and `check_valid_ins_in_ldsd()` to select the oldest ready instruction in ROB order and ensure instructions wait at least one cycle after issue and CDB broadcast before executing.
   - Here we reordered the pipeline calls in `main.py` to `commit -> wb -> mem -> exe -> issue` and added configuration parsing plus final `REGISTER VALUES` and `NON-ZERO MEMORY VALUES` output tables.

---

## 3. Simulation Results

### 3.1 Test Case #01
**Configuration:**
- Integer Adder: 4 RS, 1 EX cycle, 1 FU
- FP Adder: 4 RS, 3 EX cycles, 1 FU
- FP Multiplier: 4 RS, 5 EX cycles, 1 FU
- Load/Store Unit: 4 entries, 1 EX cycle, 6 MEM cycles, 1 FU
- ROB Entries = 64
- Initial State: `R1=12, R2=32, F0=2.0, F20=3.0`, `Mem[4]=3.0, Mem[8]=2.0, Mem[12]=1.0, Mem[20]=5.0, Mem[24]=6.0, Mem[28]=5.0, Mem[32]=4.0`

#### Test Case #01 — Issue Width = 1
```text
                              ISSUE          EXE            MEM            WB             COMMIT         
Ld F1 0(R1)                   [1]            [2, 2]         [3, 8]         [9]            [10]
Mult.d F2 F1 F0               [2]            [10, 14]       []             [15]           [16]
Add.d F3 F3 F2                [3]            [16, 18]       []             [19]           [20]
Mult.d F2 F1 F1               [4]            [11, 15]       []             [17]           [21]
Add.d F4 F2 F4                [5]            [18, 20]       []             [21]           [22]
Addi R1 R1 8                  [6]            [7, 7]         []             [8]            [23]
Ld F1 0(R1)                   [7]            [9, 9]         [10, 15]       [16]           [24]
Mult.d F2 F1 F0               [8]            [17, 21]       []             [23]           [25]
Add.d F3 F3 F2                [9]            [24, 26]       []             [27]           [28]
Mult.d F2 F1 F1               [10]           [18, 22]       []             [24]           [29]
Add.d F4 F2 F4                [11]           [25, 27]       []             [28]           [30]
Addi R1 R1 8                  [12]           [13, 13]       []             [14]           [31]
Ld F1 0(R1)                   [13]           [15, 15]       [16, 21]       [22]           [32]
Mult.d F2 F1 F0               [14]           [23, 27]       []             [29]           [33]
Add.d F3 F3 F2                [16]           [30, 32]       []             [33]           [34]
Mult.d F2 F1 F1               [17]           [24, 28]       []             [30]           [35]
Add.d F4 F2 F4                [18]           [31, 33]       []             [34]           [36]

REGISTER VALUES
R0      R1      R2      
0       28      32      
F0      F1      F2      F3      F4      F6      F20     
2.0     5.0     25.0    22.0    51.0    0       3.0     

NON-ZERO MEMORY VALUES
Addresses      Values
4              3.0
8              2.0
12             1.0
20             5.0
24             6.0
28             5.0
32             4.0
```

#### Test Case #01 — Issue Width = 2
```text
                              ISSUE          EXE            MEM            WB             COMMIT         
Ld F1 0(R1)                   [1]            [2, 2]         [3, 8]         [9]            [10]
Mult.d F2 F1 F0               [1]            [10, 14]       []             [15]           [16]
Add.d F3 F3 F2                [2]            [16, 18]       []             [19]           [20]
Mult.d F2 F1 F1               [2]            [11, 15]       []             [16]           [20]
Add.d F4 F2 F4                [3]            [17, 19]       []             [20]           [21]
Addi R1 R1 8                  [3]            [4, 4]         []             [5]            [21]
Ld F1 0(R1)                   [4]            [6, 6]         [8, 13]        [14]           [22]
Mult.d F2 F1 F0               [4]            [15, 19]       []             [20]           [22]
Add.d F3 F3 F2                [5]            [21, 23]       []             [24]           [25]
Mult.d F2 F1 F1               [5]            [16, 20]       []             [21]           [25]
Add.d F4 F2 F4                [6]            [22, 24]       []             [25]           [26]
Addi R1 R1 8                  [6]            [7, 7]         []             [8]            [26]
Ld F1 0(R1)                   [7]            [9, 9]         [13, 18]       [19]           [27]
Mult.d F2 F1 F0               [10]           [20, 24]       []             [25]           [27]
Add.d F3 F3 F2                [16]           [26, 28]       []             [29]           [30]
Mult.d F2 F1 F1               [16]           [21, 25]       []             [26]           [30]
Add.d F4 F2 F4                [17]           [27, 29]       []             [30]           [31]

REGISTER VALUES
R0      R1      R2      
0       28      32      
F0      F1      F2      F3      F4      F6      F20     
2.0     5.0     25.0    22.0    51.0    0       3.0     

NON-ZERO MEMORY VALUES
Addresses      Values
4              3.0
8              2.0
12             1.0
20             5.0
24             6.0
28             5.0
32             4.0
```

#### Test Case #01 — Issue Width = 3
```text
                              ISSUE          EXE            MEM            WB             COMMIT         
Ld F1 0(R1)                   [1]            [2, 2]         [3, 8]         [9]            [10]
Mult.d F2 F1 F0               [1]            [10, 14]       []             [15]           [16]
Add.d F3 F3 F2                [1]            [16, 18]       []             [19]           [20]
Mult.d F2 F1 F1               [2]            [11, 15]       []             [16]           [20]
Add.d F4 F2 F4                [2]            [17, 19]       []             [20]           [21]
Addi R1 R1 8                  [2]            [3, 3]         []             [4]            [21]
Ld F1 0(R1)                   [3]            [5, 5]         [8, 13]        [14]           [21]
Mult.d F2 F1 F0               [3]            [15, 19]       []             [20]           [22]
Add.d F3 F3 F2                [3]            [21, 23]       []             [24]           [25]
Mult.d F2 F1 F1               [4]            [16, 20]       []             [21]           [25]
Add.d F4 F2 F4                [4]            [22, 24]       []             [25]           [26]
Addi R1 R1 8                  [4]            [5, 5]         []             [6]            [26]
Ld F1 0(R1)                   [5]            [7, 7]         [13, 18]       [19]           [26]
Mult.d F2 F1 F0               [10]           [20, 24]       []             [25]           [27]
Add.d F3 F3 F2                [16]           [26, 28]       []             [29]           [30]
Mult.d F2 F1 F1               [16]           [21, 25]       []             [26]           [30]
Add.d F4 F2 F4                [17]           [27, 29]       []             [30]           [31]

REGISTER VALUES
R0      R1      R2      
0       28      32      
F0      F1      F2      F3      F4      F6      F20     
2.0     5.0     25.0    22.0    51.0    0       3.0     

NON-ZERO MEMORY VALUES
Addresses      Values
4              3.0
8              2.0
12             1.0
20             5.0
24             6.0
28             5.0
32             4.0
```

#### Test Case #01 — Issue Width = 4
```text
                              ISSUE          EXE            MEM            WB             COMMIT         
Ld F1 0(R1)                   [1]            [2, 2]         [3, 8]         [9]            [10]
Mult.d F2 F1 F0               [1]            [10, 14]       []             [15]           [16]
Add.d F3 F3 F2                [1]            [16, 18]       []             [19]           [20]
Mult.d F2 F1 F1               [1]            [11, 15]       []             [16]           [20]
Add.d F4 F2 F4                [2]            [17, 19]       []             [20]           [21]
Addi R1 R1 8                  [2]            [3, 3]         []             [4]            [21]
Ld F1 0(R1)                   [2]            [5, 5]         [8, 13]        [14]           [21]
Mult.d F2 F1 F0               [2]            [15, 19]       []             [20]           [21]
Add.d F3 F3 F2                [3]            [21, 23]       []             [24]           [25]
Mult.d F2 F1 F1               [3]            [16, 20]       []             [21]           [25]
Add.d F4 F2 F4                [3]            [22, 24]       []             [25]           [26]
Addi R1 R1 8                  [3]            [5, 5]         []             [6]            [26]
Ld F1 0(R1)                   [4]            [7, 7]         [13, 18]       [19]           [26]
Mult.d F2 F1 F0               [10]           [20, 24]       []             [25]           [26]
Add.d F3 F3 F2                [16]           [26, 28]       []             [29]           [30]
Mult.d F2 F1 F1               [16]           [21, 25]       []             [26]           [30]
Add.d F4 F2 F4                [17]           [27, 29]       []             [30]           [31]

REGISTER VALUES
R0      R1      R2      
0       28      32      
F0      F1      F2      F3      F4      F6      F20     
2.0     5.0     25.0    22.0    51.0    0       3.0     

NON-ZERO MEMORY VALUES
Addresses      Values
4              3.0
8              2.0
12             1.0
20             5.0
24             6.0
28             5.0
32             4.0
```

---

### 3.2 Test Case #02
**Configuration:**
- Integer Adder: 4 RS, 1 EX cycle, 1 FU
- FP Adder: 3 RS, 3 EX cycles, 2 FUs
- FP Multiplier: 2 RS, 15 EX cycles, 2 FUs
- Load/Store Unit: 4 entries, 1 EX cycle, 5 MEM cycles, 2 FUs
- ROB Entries = 128
- Initial State: `R1=12, R2=32, F0=2.0, F20=3.0`, `Mem[4]=3.0, Mem[8]=2.0, Mem[12]=1.0, Mem[16]=2.0, Mem[24]=6.0, Mem[28]=5.0, Mem[32]=4.0`

#### Test Case #02 — Issue Width = 1
```text
                              ISSUE          EXE            MEM            WB             COMMIT         
Ld F1 0(R1)                   [1]            [2, 2]         [3, 7]         [8]            [9]
Mult.d F2 F1 F0               [2]            [9, 23]        []             [24]           [25]
Add.d F3 F3 F2                [3]            [25, 27]       []             [28]           [29]
Mult.d F2 F1 F1               [4]            [9, 23]        []             [25]           [30]
Ld F1 0(R1)                   [5]            [6, 6]         [7, 11]        [12]           [31]
Addi R1 R1 4                  [6]            [7, 7]         []             [9]            [32]
Add.d F4 F2 F4                [7]            [26, 28]       []             [29]           [33]
Addi R1 R1 8                  [8]            [10, 10]       []             [11]           [34]
Ld F1 0(R1)                   [9]            [12, 12]       [13, 17]       [18]           [35]
Mult.d F2 F1 F0               [10]           [19, 33]       []             [34]           [36]
Add.d F3 F3 F2                [11]           [35, 37]       []             [38]           [39]
Mult.d F2 F1 F1               [12]           [19, 33]       []             [35]           [40]
Ld F1 0(R1)                   [13]           [14, 14]       [17, 21]       [22]           [41]
Mult.d F2 F1 F0               [19]           [23, 37]       []             [39]           [42]
Add.d F3 F3 F2                [25]           [40, 42]       []             [43]           [44]
Mult.d F2 F1 F1               [26]           [27, 41]       []             [42]           [45]
Add.d F4 F2 F4                [27]           [43, 45]       []             [46]           [47]

REGISTER VALUES
R0      R1      R2      
0       24      32      
F0      F1      F2      F3      F4      F6      F20     
2.0     6.0     36.0    26.0    37.0    0       3.0     

NON-ZERO MEMORY VALUES
Addresses      Values
4              3.0
8              2.0
12             1.0
16             2.0
24             6.0
28             5.0
32             4.0
```

#### Test Case #02 — Issue Width = 2
```text
                              ISSUE          EXE            MEM            WB             COMMIT         
Ld F1 0(R1)                   [1]            [2, 2]         [3, 7]         [8]            [9]
Mult.d F2 F1 F0               [1]            [9, 23]        []             [24]           [25]
Add.d F3 F3 F2                [2]            [25, 27]       []             [28]           [29]
Mult.d F2 F1 F1               [2]            [9, 23]        []             [24]           [29]
Ld F1 0(R1)                   [3]            [4, 4]         [7, 11]        [12]           [30]
Addi R1 R1 4                  [3]            [4, 4]         []             [5]            [30]
Add.d F4 F2 F4                [4]            [25, 27]       []             [28]           [31]
Addi R1 R1 8                  [4]            [6, 6]         []             [7]            [31]
Ld F1 0(R1)                   [5]            [8, 8]         [11, 15]       [16]           [32]
Mult.d F2 F1 F0               [9]            [17, 31]       []             [32]           [33]
Add.d F3 F3 F2                [9]            [33, 35]       []             [36]           [37]
Mult.d F2 F1 F1               [10]           [17, 31]       []             [32]           [37]
Ld F1 0(R1)                   [10]           [11, 11]       [15, 19]       [20]           [38]
Mult.d F2 F1 F0               [17]           [21, 35]       []             [36]           [38]
Add.d F3 F3 F2                [25]           [37, 39]       []             [40]           [41]
Mult.d F2 F1 F1               [25]           [26, 40]       []             [41]           [42]
Add.d F4 F2 F4                [26]           [42, 44]       []             [45]           [46]

REGISTER VALUES
R0      R1      R2      
0       24      32      
F0      F1      F2      F3      F4      F6      F20     
2.0     6.0     36.0    26.0    37.0    0       3.0     

NON-ZERO MEMORY VALUES
Addresses      Values
4              3.0
8              2.0
12             1.0
16             2.0
24             6.0
28             5.0
32             4.0
```

#### Test Case #02 — Issue Width = 3
```text
                              ISSUE          EXE            MEM            WB             COMMIT         
Ld F1 0(R1)                   [1]            [2, 2]         [3, 7]         [8]            [9]
Mult.d F2 F1 F0               [1]            [9, 23]        []             [24]           [25]
Add.d F3 F3 F2                [1]            [25, 27]       []             [28]           [29]
Mult.d F2 F1 F1               [2]            [9, 23]        []             [24]           [29]
Ld F1 0(R1)                   [2]            [3, 3]         [7, 11]        [12]           [29]
Addi R1 R1 4                  [2]            [3, 3]         []             [4]            [30]
Add.d F4 F2 F4                [3]            [25, 27]       []             [28]           [30]
Addi R1 R1 8                  [3]            [5, 5]         []             [6]            [30]
Ld F1 0(R1)                   [3]            [7, 7]         [11, 15]       [16]           [31]
Mult.d F2 F1 F0               [9]            [17, 31]       []             [32]           [33]
Add.d F3 F3 F2                [9]            [33, 35]       []             [36]           [37]
Mult.d F2 F1 F1               [9]            [17, 31]       []             [32]           [37]
Ld F1 0(R1)                   [10]           [11, 11]       [15, 19]       [20]           [37]
Mult.d F2 F1 F0               [17]           [21, 35]       []             [36]           [38]
Add.d F3 F3 F2                [25]           [37, 39]       []             [40]           [41]
Mult.d F2 F1 F1               [25]           [26, 40]       []             [41]           [42]
Add.d F4 F2 F4                [25]           [42, 44]       []             [45]           [46]

REGISTER VALUES
R0      R1      R2      
0       24      32      
F0      F1      F2      F3      F4      F6      F20     
2.0     6.0     36.0    26.0    37.0    0       3.0     

NON-ZERO MEMORY VALUES
Addresses      Values
4              3.0
8              2.0
12             1.0
16             2.0
24             6.0
28             5.0
32             4.0
```

#### Test Case #02 — Issue Width = 4
```text
                              ISSUE          EXE            MEM            WB             COMMIT         
Ld F1 0(R1)                   [1]            [2, 2]         [3, 7]         [8]            [9]
Mult.d F2 F1 F0               [1]            [9, 23]        []             [24]           [25]
Add.d F3 F3 F2                [1]            [25, 27]       []             [28]           [29]
Mult.d F2 F1 F1               [1]            [9, 23]        []             [24]           [29]
Ld F1 0(R1)                   [2]            [3, 3]         [7, 11]        [12]           [29]
Addi R1 R1 4                  [2]            [3, 3]         []             [4]            [29]
Add.d F4 F2 F4                [2]            [25, 27]       []             [28]           [30]
Addi R1 R1 8                  [2]            [5, 5]         []             [6]            [30]
Ld F1 0(R1)                   [3]            [7, 7]         [11, 15]       [16]           [30]
Mult.d F2 F1 F0               [9]            [17, 31]       []             [32]           [33]
Add.d F3 F3 F2                [9]            [33, 35]       []             [36]           [37]
Mult.d F2 F1 F1               [9]            [17, 31]       []             [32]           [37]
Ld F1 0(R1)                   [9]            [10, 10]       [15, 19]       [20]           [37]
Mult.d F2 F1 F0               [17]           [21, 35]       []             [36]           [37]
Add.d F3 F3 F2                [25]           [37, 39]       []             [40]           [41]
Mult.d F2 F1 F1               [25]           [26, 40]       []             [41]           [42]
Add.d F4 F2 F4                [25]           [42, 44]       []             [45]           [46]

REGISTER VALUES
R0      R1      R2      
0       24      32      
F0      F1      F2      F3      F4      F6      F20     
2.0     6.0     36.0    26.0    37.0    0       3.0     

NON-ZERO MEMORY VALUES
Addresses      Values
4              3.0
8              2.0
12             1.0
16             2.0
24             6.0
28             5.0
32             4.0
```