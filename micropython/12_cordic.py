import machine
import time
import math

peripheral_num = 12
base = 0x800_0000 + 64*peripheral_num

def to_fp(v, point=14):
    return int(v * (1 << point)) & 0xffff

def from_fp(v, point=14):
    if v >= 0x8000: v -= 0x10000
    return v / (1 << point)

angle = math.pi / 6
fp_angle = to_fp(angle)
machine.mem16[base+1] = fp_angle
machine.mem8[base] = 0b1001
while machine.mem8[base+6] == 1:
    pass

c = from_fp(machine.mem16[base+4])
s = from_fp(machine.mem16[base+5])
print(f"cos({angle * 180 / math.pi}) = {c}, sin({angle * 180 / math.pi}) = {s}")

a = to_fp(7, 11)
b = to_fp(5, 11)
machine.mem16[base+1] = a
machine.mem16[base+2] = b
machine.mem8[base] = 0b0101
while machine.mem8[base+6] == 1:
    pass

r = from_fp(machine.mem16[base+4], 11)
print(f"sqrt(6) = {r}")
