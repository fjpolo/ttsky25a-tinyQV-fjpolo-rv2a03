from machine import Pin
from tinyqv import write_byte_reg

PERIPHERAL_NUM = 13

# Note don't assign Pin 0/r1 so that we keep access to UART
g1 = Pin(1, func_sel=PERIPHERAL_NUM)
b1 = Pin(2, func_sel=PERIPHERAL_NUM)
vs = Pin(3, func_sel=PERIPHERAL_NUM)
r0 = Pin(4, func_sel=PERIPHERAL_NUM)
g0 = Pin(5, func_sel=PERIPHERAL_NUM)
b0 = Pin(6, func_sel=PERIPHERAL_NUM)
hs = Pin(7, func_sel=PERIPHERAL_NUM)

def write_reg(addr, value):
    write_byte_reg(PERIPHERAL_NUM, addr, value)

# Capital letters
for i in range(10):
    write_reg(i, 65+i) 
    
# Numbers
for i in range(10):
    write_reg(10 + i, 48+i)

# A message, with alternating colours
s = b'TinyQV VGA'
for i in range(10):
    write_reg(20 + i, s[i] | (0x80 if i & 1 != 0 else 0))
