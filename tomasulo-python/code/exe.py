# Qing 
# 24th May 2017

''' 
1. calculate valid instructions
    -- for ALU instructions, write results into fu_results, remove that fu entry  
    -- for LD/SD, write address result immediately back to ld_sd_queue
2. fetch instructions into function unit with spare space
    -- remove ALU instructions from rs
    -- don't remove ld/sd instructions
'''
from init import fu_entry, fu_result

# dictionary to keep track of functional unit elements already stepped in a cycle
cycle_call_history = {}

# function: find ROB entry by tag
def find_ROB_entry(ROB, tag):
    for index in range(len(ROB)):
        if ROB[index].ROB_tag == tag:
            return index
    return 0

# function: check rs and return valid instruction index (oldest ready instruction first)
def check_valid_ins_in_rs(rs, ROB, cycle):
    index = -1
    if len(rs)!=0:
        possible_indices = []
        rob_orders = []
        for i in range(len(rs)):
            if (rs[i].valid_1st==1)&(rs[i].valid_2nd==1)&(rs[i].busy==1):
                index_r = find_ROB_entry(ROB, rs[i].dest_tag)
                # Instruction cannot execute in the same cycle it was issued
                if ROB[index_r].issue[0] < cycle:
                    possible_indices.append(i)
                    rob_orders.append(index_r)
        if len(possible_indices) > 0:
            while len(rob_orders) > 0:
                dependent = False
                min_pos = rob_orders.index(min(rob_orders))
                index_t = possible_indices[min_pos]
                index_p = find_ROB_entry(ROB, rs[index_t].dest_tag)
                selected_rob = ROB[index_p]
                for rob_x in ROB:
                    if rob_x.ROB_tag == selected_rob.ROB_tag:
                        break
                    # If an older instruction broadcasted on CDB in this exact cycle, wait 1 cycle
                    if ( getattr(rs[index_t], 'tag_1st', None) == rob_x.ROB_tag or
                         getattr(rs[index_t], 'tag_2nd', None) == rob_x.ROB_tag ):
                        if len(rob_x.cdb) == 1 and rob_x.cdb[0] == cycle:
                            dependent = True
                            break
                if not dependent:
                    index = index_t
                    break
                else:
                    rob_orders.pop(min_pos)
                    possible_indices.pop(min_pos)
    return index

# function: check ld_sd_queue and return valid instruction index
def check_valid_ins_in_ldsd(ldsd, ROB, cycle):
    index = -1
    if len(ldsd)!=0:
        for i in range(len(ldsd)):
            if (ldsd[i].valid==1) & (ldsd[i].ready==0):
                index_p = find_ROB_entry(ROB, ldsd[i].dest_tag)
                if ROB[index_p].issue[0] < cycle:
                    dependent = False
                    selected_rob = ROB[index_p]
                    for rob_x in ROB:
                        if rob_x.ROB_tag == selected_rob.ROB_tag:
                            break
                        if len(rob_x.cdb) == 1 and rob_x.cdb[0] == cycle:
                            if getattr(ldsd[i], 'reg_tag', None) == rob_x.ROB_tag:
                                dependent = True
                                break
                    if not dependent:
                        index = i
                        break
    return index

# function: add entry into fu 
def add_entry_into_fu(fu, ins_in_rs):
    fu[-1].cycle = 0
    fu[-1].op = ins_in_rs.op
    fu[-1].value1 = ins_in_rs.value_1st
    fu[-1].value2 = ins_in_rs.value_2nd
    fu[-1].dest_tag = ins_in_rs.dest_tag
    # Clear tag fields so reused RS entries don't false-match
    ins_in_rs.tag_1st = None
    ins_in_rs.tag_2nd = None

# function: functional units execution 
def fu_exe(fu, fu_results, ROB, time_fu, cycle, PC):
    if len(fu)!=0:
        for element in fu:
            if (element.dest_tag, cycle) not in cycle_call_history:
                element.cycle += 1
                cycle_call_history[(element.dest_tag, cycle)] = 1
                # write starting cycle 
                if element.cycle == 1:
                    index = find_ROB_entry(ROB, element.dest_tag)
                    ROB[index].exe.append(cycle)
        # finish cycle (check all finished elements in FIFO order)
        while len(fu) > 0 and fu[0].cycle == time_fu:
            index = find_ROB_entry(ROB, fu[0].dest_tag)
            ROB[index].exe.append(cycle)
            # calculation result
            fu_results.append(fu_result())
            fu_results[-1].dest_tag = fu[0].dest_tag
            if (fu[0].op=='Add')|(fu[0].op=='Add.d')|(fu[0].op=='Addi'):
                fu_results[-1].value = fu[0].value1 + fu[0].value2
            elif (fu[0].op=='Sub')|(fu[0].op=='Sub.d'):
                fu_results[-1].value = fu[0].value1 - fu[0].value2
            elif (fu[0].op=='Mult.d'):
                fu_results[-1].value = fu[0].value1 * fu[0].value2
            elif (fu[0].op=='Bne'):
                fu_results.pop()
                if fu[0].value1 == fu[0].value2:
                    PC.PC += 1
                    PC.valid = 1
                else:
                    index = find_ROB_entry(ROB, fu[0].dest_tag)
                    offset = ROB[index].dest_tag
                    PC.PC = int(PC.PC + 1 + offset/4)
                    PC.valid = 1
            elif (fu[0].op=='Beq'):
                fu_results.pop()
                if fu[0].value1 != fu[0].value2:
                    PC.PC += 1
                    PC.valid = 1
                else:
                    index = find_ROB_entry(ROB, fu[0].dest_tag)
                    offset = ROB[index].dest_tag
                    PC.PC = int(PC.PC + 1 + offset/4)
                    PC.valid = 1
            else:
                pass
            # remove from fu 
            fu.popleft()

# function: ld_sd_execution 
def ld_sd_execution(ld_sd_exe, time_ld_sd_exe, ld_sd_queue, ROB, cycle):
    if ld_sd_exe.busy == 1:
        # write down starting cycle
        if ld_sd_exe.cycle == 0:            
            for element in ld_sd_queue:
                if element.ld_sd_tag == ld_sd_exe.dest_tag:
                    break
            index = find_ROB_entry(ROB, element.dest_tag)
            ROB[index].exe.append(cycle)
            # execute 
            ld_sd_exe.cycle += 1
        # write address back to ld_sd_queue
        if ld_sd_exe.cycle == time_ld_sd_exe:
            address = ld_sd_exe.value1 + ld_sd_exe.value2
            for element in ld_sd_queue:
                if element.ld_sd_tag == ld_sd_exe.dest_tag:
                    element.address = address
                    element.ready = 1
                    break
            # write down finish cycle
            index = find_ROB_entry(ROB, element.dest_tag)
            ROB[index].exe.append(cycle)
            ld_sd_exe.busy = 0

# function: execution
def exe(fu_int_adder, time_fu_int_adder,
        fu_fp_adder, time_fu_fp_adder,
        fu_fp_multi, time_fu_fp_multi, results_buffer,
        rs_int_adder, rs_fp_adder, rs_fp_multi, 
        ld_sd_exe, time_ld_sd_exe, ld_sd_queue,
        cycle, ROB, PC,
        num_fu_int_adder=1, num_fu_fp_adder=1, num_fu_fp_multi=1, num_ld_sd_exe=1):
    '''execution in fu and ld_sd address calculation'''
    ld_sd_execution(ld_sd_exe, time_ld_sd_exe, ld_sd_queue, ROB, cycle) 
    # functional units 
    fu_exe(fu_int_adder, results_buffer, ROB, time_fu_int_adder, cycle, PC)
    fu_exe(fu_fp_adder, results_buffer, ROB, time_fu_fp_adder, cycle, PC)
    fu_exe(fu_fp_multi, results_buffer, ROB, time_fu_fp_multi, cycle, PC)
    '''fetch instructions from rs and ld_sd_queue'''
    # from ld_sd_queue
    for _ in range(num_ld_sd_exe):
        index = check_valid_ins_in_ldsd(ld_sd_queue, ROB, cycle)
        if (index>=0)&(ld_sd_exe.busy==0):
            ld_sd_exe.busy = 1
            ld_sd_exe.cycle = 0
            ld_sd_exe.value1 = ld_sd_queue[index].reg_value
            ld_sd_exe.value2 = ld_sd_queue[index].immediate
            ld_sd_exe.dest_tag = ld_sd_queue[index].ld_sd_tag
            if ROB[find_ROB_entry(ROB, ld_sd_queue[index].dest_tag)].issue[0] < cycle:
                ld_sd_execution(ld_sd_exe, time_ld_sd_exe, ld_sd_queue, ROB, cycle)
    # from rs: int_adder
    for _ in range(num_fu_int_adder):
        index = check_valid_ins_in_rs(rs_int_adder, ROB, cycle)
        if index >= 0:
            fu_int_adder.append(fu_entry())
            add_entry_into_fu(fu_int_adder, rs_int_adder[index])
            rs_int_adder[index].busy = 0
            if ROB[find_ROB_entry(ROB, fu_int_adder[-1].dest_tag)].issue[0] < cycle:
                fu_exe(fu_int_adder, results_buffer, ROB, time_fu_int_adder, cycle, PC)
    # from rs: fp_adder
    for _ in range(num_fu_fp_adder):
        index = check_valid_ins_in_rs(rs_fp_adder, ROB, cycle)
        if index >= 0:
            fu_fp_adder.append(fu_entry())
            add_entry_into_fu(fu_fp_adder, rs_fp_adder[index])
            rs_fp_adder[index].busy = 0
            if ROB[find_ROB_entry(ROB, fu_fp_adder[-1].dest_tag)].issue[0] < cycle:
                fu_exe(fu_fp_adder, results_buffer, ROB, time_fu_fp_adder, cycle, PC)
    # from rs: fp_multi
    for _ in range(num_fu_fp_multi):
        index = check_valid_ins_in_rs(rs_fp_multi, ROB, cycle)
        if index >= 0:
            fu_fp_multi.append(fu_entry())
            add_entry_into_fu(fu_fp_multi, rs_fp_multi[index])
            rs_fp_multi[index].busy = 0
            if ROB[find_ROB_entry(ROB, fu_fp_multi[-1].dest_tag)].issue[0] < cycle:
                fu_exe(fu_fp_multi, results_buffer, ROB, time_fu_fp_multi, cycle, PC)