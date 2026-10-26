# Qing 
# 21st May 2017 

import sys
import re
from copy import deepcopy
from collections import deque, namedtuple
from init import read_instruction, build_rs, ld_sd_entry, ld_sd_exe, ld_sd_mem, cdb, ROB_entry, PC
from print_status import ps, pss
import exe as exe_module
from issue import issue, check_rs_space
from exe import exe 
from mem import mem
from wb import wb 
from commit import commit

def parse_input_file(filename):
    # Default configuration matching original main.py
    config = {
        'rs_int_adder': 4, 'time_int_adder': 1, 'fu_int_adder': 1,
        'rs_fp_adder': 3,  'time_fp_adder': 4,  'fu_fp_adder': 1,
        'rs_fp_multi': 2,  'time_fp_multi': 15, 'fu_fp_multi': 1,
        'size_ld_sd': 5,   'time_ld_sd_exe': 1, 'time_ld_sd_mem': 5, 'fu_ld_sd': 1,
        'size_ROB': 64,
        'issue_width': 1,
        'reg_int': [0]*32,
        'reg_fp': [0]*32,
        'memory': [0]*256,
        'instructions': []
    }
    config['reg_int'][1] = 12
    config['reg_int'][2] = 32
    config['reg_fp'][20] = 3.0
    config['memory'][4]  = 3.0
    config['memory'][8]  = 2.0
    config['memory'][12] = 1.0
    config['memory'][24] = 6.0
    config['memory'][28] = 5.0
    config['memory'][32] = 4.0

    with open(filename, 'r') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    has_config_header = any('ROB entries' in l or 'Integer adder' in l for l in lines)
    if has_config_header:
        config['reg_int'] = [0]*32
        config['reg_fp']  = [0]*32
        config['memory']  = [0]*256

    for line in lines:
        low = line.lower()
        if low.startswith('#') or 'cycles in ex' in low:
            continue
        elif low.startswith('integer adder'):
            nums = [int(x) for x in re.findall(r'\d+', line)]
            config['rs_int_adder'], config['time_int_adder'], config['fu_int_adder'] = nums[0], nums[1], nums[2]
        elif low.startswith('fp adder'):
            nums = [int(x) for x in re.findall(r'\d+', line)]
            config['rs_fp_adder'], config['time_fp_adder'], config['fu_fp_adder'] = nums[0], nums[1], nums[2]
        elif low.startswith('fp multiplier'):
            nums = [int(x) for x in re.findall(r'\d+', line)]
            config['rs_fp_multi'], config['time_fp_multi'], config['fu_fp_multi'] = nums[0], nums[1], nums[2]
        elif low.startswith('load/store unit'):
            nums = [int(x) for x in re.findall(r'\d+', line)]
            config['size_ld_sd'], config['time_ld_sd_exe'], config['time_ld_sd_mem'], config['fu_ld_sd'] = nums[0], nums[1], nums[2], nums[3]
        elif low.startswith('rob entries'):
            config['size_ROB'] = int(re.findall(r'\d+', line)[0])
        elif low.startswith('issue width'):
            config['issue_width'] = int(re.findall(r'\d+', line)[0])
        elif low.startswith('mem['):
            for m_idx, m_val in re.findall(r'Mem\[\s*(\d+)\s*\]\s*=\s*([0-9.-]+)', line, re.IGNORECASE):
                config['memory'][int(m_idx)] = float(m_val)
        elif re.match(r'^[RF]\d+\s*=', line, re.IGNORECASE):
            for r_type, r_idx, r_val in re.findall(r'([RF])\s*(\d+)\s*=\s*([0-9.-]+)', line, re.IGNORECASE):
                if r_type.upper() == 'R':
                    config['reg_int'][int(r_idx)] = int(float(r_val))
                else:
                    config['reg_fp'][int(r_idx)] = float(r_val)
        else:
            config['instructions'].append(line)

    return config

def run_simulation(input_file='code.in', override_issue_width=None):
    exe_module.cycle_call_history.clear()
    cfg = parse_input_file(input_file)

    issue_width = override_issue_width if override_issue_width is not None else cfg['issue_width']
    instructions = cfg['instructions']
    reg_int = cfg['reg_int']
    rat_int = deepcopy(reg_int)
    reg_fp  = cfg['reg_fp']
    rat_fp  = deepcopy(reg_fp)
    memory  = cfg['memory']

    rs_int_adder = build_rs(cfg['rs_int_adder'])
    rs_fp_adder  = build_rs(cfg['rs_fp_adder'])
    rs_fp_multi  = build_rs(cfg['rs_fp_multi'])

    fu_int_adder = deque()
    time_fu_int_adder = cfg['time_int_adder']
    fu_fp_adder = deque()
    time_fu_fp_adder = cfg['time_fp_adder']
    fu_fp_multi = deque()
    time_fu_fp_multi = cfg['time_fp_multi']

    ld_sd_queue = deque()
    size_ld_sd_queue = cfg['size_ld_sd']
    ld_sd_exe_unit = ld_sd_exe()
    ld_sd_exe_unit.busy = 0
    time_ld_sd_exe = cfg['time_ld_sd_exe']
    ld_sd_mem_unit = ld_sd_mem()
    ld_sd_mem_unit.busy = 0
    time_ld_sd_mem = cfg['time_ld_sd_mem']

    ROB = deque()
    size_ROB = cfg['size_ROB']

    results_buffer = deque()
    cdb_bus = cdb()
    cdb_bus.valid = 0

    pc_reg = PC()
    pc_reg.PC = 0
    pc_reg.valid = 1
    cycle = 1

    # print title 
    item = ''.ljust(30)
    item += 'ISSUE'.ljust(15)
    item += 'EXE'.ljust(15)
    item += 'MEM'.ljust(15)
    item += 'WB'.ljust(15)
    item += 'COMMIT'.ljust(15)
    print(item)

    # main loop (stages called in reverse pipeline order: commit -> wb -> mem -> exe -> issue)
    while (len(ROB) > 0) or (cycle == 1) or (pc_reg.PC < len(instructions) and pc_reg.valid == 1):
        '''COMMIT stage'''
        commit(ROB, reg_int, reg_fp, cycle, instructions, issue_width)

        '''CDB / WB stage'''
        wb(cdb_bus, rat_int, rat_fp, 
            rs_int_adder, rs_fp_adder, rs_fp_multi,
            ld_sd_queue, ROB, cycle,
            results_buffer, issue_width)

        '''MEM stage'''
        mem(ld_sd_queue, ld_sd_mem_unit, time_ld_sd_mem, results_buffer,
            memory, ROB, cycle)

        '''EXE stage'''
        exe(fu_int_adder, time_fu_int_adder, 
            fu_fp_adder, time_fu_fp_adder, 
            fu_fp_multi, time_fu_fp_multi, results_buffer,  
            rs_int_adder, rs_fp_adder, rs_fp_multi, 
            ld_sd_exe_unit, time_ld_sd_exe, ld_sd_queue,
            cycle, ROB, pc_reg,
            cfg['fu_int_adder'], cfg['fu_fp_adder'], cfg['fu_fp_multi'], cfg['fu_ld_sd'])

        '''ISSUE stage'''
        if (pc_reg.PC < len(instructions)) and (pc_reg.valid == 1):
            issue(cycle, pc_reg, instructions, ROB, size_ROB, 
                    rs_int_adder, 
                    rs_fp_adder, 
                    rs_fp_multi, 
                    ld_sd_queue, size_ld_sd_queue, 
                    rat_int, rat_fp, issue_width)

        cycle += 1

    # Print final Register and Non-Zero Memory Values
    print('\nREGISTER VALUES')
    int_headers = ''.join([f'R{i}'.ljust(8) for i in range(32) if reg_int[i] != 0 or i in (0, 1, 2)])
    int_vals    = ''.join([f'{reg_int[i]}'.ljust(8) for i in range(32) if reg_int[i] != 0 or i in (0, 1, 2)])
    print(int_headers)
    print(int_vals)

    fp_headers  = ''.join([f'F{i}'.ljust(8) for i in range(32) if reg_fp[i] != 0 or i in (0, 1, 2, 3, 4, 6, 20)])
    fp_vals     = ''.join([f'{reg_fp[i]}'.ljust(8) for i in range(32) if reg_fp[i] != 0 or i in (0, 1, 2, 3, 4, 6, 20)])
    print(fp_headers)
    print(fp_vals)

    print('\nNON-ZERO MEMORY VALUES')
    print('Addresses'.ljust(15) + 'Values')
    for addr in range(len(memory)):
        if memory[addr] != 0:
            print(str(addr).ljust(15) + str(memory[addr]))

if __name__ == '__main__':
    infile = sys.argv[1] if len(sys.argv) > 1 else 'code.in'
    iw = int(sys.argv[2]) if len(sys.argv) > 2 else None
    run_simulation(infile, iw)