# Qing 
# 29th may 2017
'''
1. commit ROB_buffer (up to issue_width instructions per cycle)
2. fetch header into ROB_buffer
'''

# function: print ROB entry 
def print_ROB(entry, instructions):
    item = instructions[entry.PC].ljust(30)
    item += str(entry.issue).ljust(15) 
    item += str(entry.exe).ljust(15) 
    item += str(entry.mem).ljust(15)
    item += str(entry.cdb).ljust(15)
    item += str(entry.commit)
    print(item)

# function: modify architectual reg
def modify_arch_reg(entry, reg_int, reg_fp):
    dest = str(entry.dest_tag)
    if dest[0] == 'F':
        reg_fp[int(dest[1:])] = entry.value
    elif dest[0] == 'R':
        if int(dest[1:]) != 0:
            reg_int[int(dest[1:])] = entry.value
    else:
        pass

# function: commit
def commit(ROB, reg_int, reg_fp, cycle, instructions, issue_width=1):
    for _ in range(issue_width):
        if len(ROB) > 0:
            op = instructions[ROB[0].PC].replace(',', ' ').split()[0]
            if (op=='Bne')|(op=='Beq'):
                if len(ROB[0].exe) != 0 and ROB[0].exe[-1] < cycle:
                    ROB[0].commit.append(cycle)
                    entry = ROB.popleft()
                    print_ROB(entry, instructions)
                else:
                    break
            else:
                if len(ROB[0].cdb) != 0 and ROB[0].cdb[0] < cycle: # broadcasted in a prior cycle
                    ROB[0].commit.append(cycle)
                    entry = ROB.popleft()
                    modify_arch_reg(entry, reg_int, reg_fp)
                    print_ROB(entry, instructions)
                elif len(ROB[0].commit) != 0 and ROB[0].commit[0] < cycle: # Sd finished mem
                    entry = ROB.popleft()
                    print_ROB(entry, instructions)
                else:
                    break