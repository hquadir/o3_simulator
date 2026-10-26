# Multiple-Issue Tomasulo Algorithm Simulator

This is a Python implementation of the Tomasulo dynamic instruction scheduling algorithm with Reorder Buffer (ROB), Register Alias Table (RAT), Load/Store Queue with store-to-load forwarding, and superscalar multi-issue support (`Issue width = 1` to `4`).

## Files in Repository
- `main.py`: This contains the Entry point, input configuration parser, main clock-cycle driver loop, and architectural state printer.
- `init.py`: This contains the Data structure definitions for reservation stations (`rs_entry`), functional units (`fu_entry`), load/store queue (`ld_sd_entry`), CDB, and ROB (`ROB_entry`).
- `issue.py`: This contains the Multi-instruction in-order `issue()` stage supporting issue widths 1 to 4.
- `exe.py`: This contains the Out-of-order functional unit execution stage supporting multiple pipelined/unpipelined functional units.
- `mem.py`: This contains the Load/store memory access stage and store-to-load data forwarding logic.
- `wb.py`: This contains Common Data Bus (CDB) multi-instruction write-back and broadcast logic.
- `commit.py`: This contains the In-order ROB multi-instruction commit stage.
- `print_status.py`: This contains Helper functions for printing reservation station and ROB status.
- `test_case.txt`, `test_case_1.txt`, `test_case_2.txt`, `code.in`: This contains Hardware configuration and instruction benchmark files.
- `REPORT.md`: This contains the Assignment report detailing code changes and simulation results across issue widths 1 to 4.

## How to Run

Run `main.py` with Python 3, passing the test case file and an optional issue width (`1` to `4`) as shown below:

```bash
# Baseline test case with loop and branch
python3 main.py test_case.txt 1

# Test Case 1 across Issue Widths 1, 2, 3, and 4
python3 main.py test_case_1.txt 1
python3 main.py test_case_1.txt 2
python3 main.py test_case_1.txt 3
python3 main.py test_case_1.txt 4

# Test Case 2 across Issue Widths 1, 2, 3, and 4
python3 main.py test_case_2.txt 1
python3 main.py test_case_2.txt 2
python3 main.py test_case_2.txt 3
python3 main.py test_case_2.txt 4
```