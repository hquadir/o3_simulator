# Qing 
# 29th May 2017 

'''
1. broadcast data on cdb (up to issue_width instructions per cycle)
2. fetch data from results queue 
3. remove entry in results queue
'''
# function: find ROB entry by tag
def find_ROB_entry(ROB, tag):
    for index in range(len(ROB)):
        if ROB[index].ROB_tag == tag:
            return index
    return 0

# function: boroadcast
# rat_int, rat_fp, reservation stations, ld_sd_queue, ROB
def boroadcast(cdb, rat_int, rat_fp, 
                rs_int_adder, rs_fp_adder, rs_fp_multi,
                ld_sd_queue, ROB, cycle):
    # dest_tag
    dest_tag = cdb.dest_tag
    index = find_ROB_entry(ROB, dest_tag)
    reg_tag = str(ROB[index].dest_tag)
    # rat_int (only update RAT if it still points to this ROB entry)
    if reg_tag[0] == 'R':
        reg_num = int(reg_tag[1:])
        if rat_int[reg_num] == dest_tag:
            rat_int[reg_num] = cdb.value
    # rat_fp (only update RAT if it still points to this ROB entry)
    if reg_tag[0] == 'F':
        reg_num = int(reg_tag[1:])
        if rat_fp[reg_num] == dest_tag:
            rat_fp[reg_num] = cdb.value 
    # rs list
    rs_list = [rs_int_adder, rs_fp_adder, rs_fp_multi]
    for rs in rs_list:
        for element in rs:
            if (getattr(element, 'tag_1st', None)==dest_tag)&(getattr(element, 'valid_1st', 1)==0):
                element.value_1st = cdb.value
                element.valid_1st = 1
            if (getattr(element, 'tag_2nd', None)==dest_tag)&(getattr(element, 'valid_2nd', 1)==0):
                element.value_2nd = cdb.value
                element.valid_2nd = 1
    # ld_sd_queue 
    for element in ld_sd_queue:
        if (element.data==dest_tag)&(element.op=='Sd'):
            element.data = cdb.value
        if (getattr(element, 'reg_tag', None)==dest_tag)&(element.valid==0):
            element.reg_value = cdb.value
            element.valid = 1
    # ROB
    for element in ROB:
        if element.ROB_tag == dest_tag:
            element.value = cdb.value
            element.cdb.append(cycle)

# function: wb 
def wb(cdb, rat_int, rat_fp, 
        rs_int_adder, rs_fp_adder, rs_fp_multi,
        ld_sd_queue, ROB, cycle,
        results_buffer, issue_width=1):
    # broadcast up to issue_width results per cycle
    bd_count = 0
    while len(results_buffer) > 0 and (bd_count < issue_width):
        cdb.valid = 1
        cdb.value = results_buffer[0].value
        cdb.dest_tag = results_buffer[0].dest_tag
        results_buffer.popleft()
        boroadcast(cdb, rat_int, rat_fp, 
                    rs_int_adder, rs_fp_adder, rs_fp_multi,
                    ld_sd_queue, ROB, cycle)
        cdb.valid = 0
        bd_count += 1