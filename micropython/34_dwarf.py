import machine
import time
from tinyqv import get_base_address

peripheral_num = 34
base = get_base_address(peripheral_num)
PROG_HDR = base
PROG_CODE = base + 0x4
AM_ADDR = base + 0x8
AM_FILE_DISCRIM = base + 0xc
AM_LINE_COL_FLAGS = base + 0x10
STATUS = base + 0x14
INFO = base + 0x18

print(machine.mem32[INFO])
print(machine.mem32[STATUS])

machine.mem32[PROG_HDR] = 0x0D07FD00
machine.mem16[PROG_CODE] = 0x6f04
print(machine.mem32[AM_FILE_DISCRIM])

machine.mem32[PROG_CODE] = 0x37040200
print(machine.mem32[AM_FILE_DISCRIM])
