# SPDX-License-Identifier: Apache-2.0
# Author: Rebecca G. Bettencourt

# To use:
# 1. Run the test() function to verify that the peripheral is working correctly:
#    mpremote <port> run 23_ubcd.py exec 'test()'
# 2. Run the display_test() function to loop through glyphs on the 7-segment
#    display. This will disrupt the serial console output and loop forever.
#    mpremote <port> run 23_ubcd.py exec 'display_test()'
# 3. Run the display_message() function to display a message on the 7-segment
#    display. This will disrupt the serial console output temporarily.
#    mpremote <port> run 23_ubcd.py exec 'display_message("HELLO TINY TAPEOUT")'
# 4. Import as a library to use the init(), write(), set_mode(), read(),
#    set_display_on(), etc. functions.

import machine
import time
import tinyqv

PERIPHERAL_NUM = 23
BASE = tinyqv.get_base_address(PERIPHERAL_NUM)

# Register 1 (Display Control Register)
DP0 = 0x01
DP1 = 0x02
DP2 = 0x04
DP3 = 0x08
AL  = 0x10
BI  = 0x20
LT  = 0x40
RBI = 0x80

# Register 2 (Variant Control Register)
V0 = 0x01
V1 = 0x02
V2 = 0x04
FS = 0x08
LC = 0x10
X6 = 0x20
X7 = 0x40
X9 = 0x80

BLANKING    = 0x00
RCA         = 0x00
TI          = 0x01
NATSEMI     = 0x02
TOSHIBA     = 0x03
LINES       = 0x04
ELECTRONIKA = 0x05
CODE_B      = 0x06
HEX         = 0x07
HEXADECIMAL = 0x07

# Register 3 (Peripheral Control Register)
M0 = 0x01
M1 = 0x02
M2 = 0x04
OE = 0x40
LE = 0x80

BCD_ONES = 0x00
BCD_TENS = 0x01
ASCII    = 0x02
PASSTHRU = 0x03
CIS_ONES = 0x04
CIS_TENS = 0x05
KAKTOVIK = 0x06
PASSTHRU = 0x07

# Register 5 (Status Register)
LTR = 0x20
V   = 0x40
RBO = 0x80

def init():
	machine.mem8[BASE] = 0
	machine.mem8[BASE+1] = AL|BI|LT|RBI
	machine.mem8[BASE+2] = LC|X6|X7|X9
	machine.mem8[BASE+3] = 0

def write(b):
	machine.mem8[BASE] = b

def write_dp(b):
	machine.mem8[BASE+1] = (machine.mem8[BASE+1] & 0xF0) | (b & 0x0F)

def set_al(b):
	if b:
		machine.mem8[BASE+1] |= AL
	else:
		machine.mem8[BASE+1] &=~ AL

def set_bi(b):
	if b:
		machine.mem8[BASE+1] |= BI
	else:
		machine.mem8[BASE+1] &=~ BI

def set_lt(b):
	if b:
		machine.mem8[BASE+1] |= LT
	else:
		machine.mem8[BASE+1] &=~ LT

def set_rbi(b):
	if b:
		machine.mem8[BASE+1] |= RBI
	else:
		machine.mem8[BASE+1] &=~ RBI

def set_bcd_variant(b):
	machine.mem8[BASE+2] = (machine.mem8[BASE+2] & 0xF8) | (b & 0x07)

def set_ascii_font(b):
	if b:
		machine.mem8[BASE+2] |= FS
	else:
		machine.mem8[BASE+2] &=~ FS

def set_lowercase(b):
	if b:
		machine.mem8[BASE+2] |= LC
	else:
		machine.mem8[BASE+2] &=~ LC

def set_extra_segments(b):
	machine.mem8[BASE+2] = (machine.mem8[BASE+2] & 0x1F) | (b & 0xE0)

def set_mode(b):
	machine.mem8[BASE+3] = (machine.mem8[BASE+3] & 0xF8) | (b & 0x07)

def set_oe(b):
	if b:
		machine.mem8[BASE+3] |= OE
	else:
		machine.mem8[BASE+3] &=~ OE

def set_le(b):
	if b:
		machine.mem8[BASE+3] |= LE
	else:
		machine.mem8[BASE+3] &=~ LE

def read():
	return machine.mem8[BASE+4]

def read_dp():
	return machine.mem8[BASE+5] & 0x0F

def get_ltr():
	return machine.mem8[BASE+5] & LTR

def get_v():
	return machine.mem8[BASE+5] & V

def get_rbo():
	return machine.mem8[BASE+5] & RBO

def set_display_on(en):
	machine.Pin(0, func_sel=PERIPHERAL_NUM if en else 2)
	for i in range(1, 8):
		machine.Pin(i, func_sel=PERIPHERAL_NUM if en else 0)

# Tests

def test_equal(actual, expected):
	global passed
	global failed
	if actual == expected:
		passed += 1
	else:
		print(f"NG: {actual} != {expected}")
		failed += 1

def test():
	global passed
	global failed
	passed = 0
	failed = 0
	# Initial State
	init()
	test_equal(read(), 0x3F)
	# Blanking Input
	set_bi(0)
	test_equal(read(), 0x00)
	set_bi(1)
	test_equal(read(), 0x3F)
	# Lamp Test
	set_lt(0)
	test_equal(read(), 0xFF)
	set_lt(1)
	test_equal(read(), 0x3F)
	# Passthrough Mode
	set_mode(PASSTHRU)
	expected = [0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0xFF]
	for i in expected:
		write(i)
		test_equal(read(), i)
	# Kaktovik Mode
	set_mode(KAKTOVIK)
	expected = [0x04, 0x01, 0x07, 0x0F, 0x1F, 0x20, 0x21, 0x27, 0x2F, 0x3F, 0x60, 0x61, 0x67, 0x6F, 0x7F, 0xE0, 0xE1, 0xE7, 0xEF, 0xFF]
	for i in range(20):
		write(i)
		test_equal(read(), expected[i])
	# Cistercian Mode
	set_mode(CIS_ONES)
	expected = [0b00000, 0b00001, 0b00010, 0b00100, 0b01000, 0b01001, 0b10000, 0b10001, 0b10010, 0b10011]
	for i in range(10):
		write(i)
		test_equal(read(), expected[i])
	# ASCII Mode
	set_mode(ASCII)
	expected = [
		0x00, 0x0A, 0x22, 0x36, 0x2D, 0x24, 0x78, 0x42, 0x39, 0x0F, 0x63, 0x46, 0x0C, 0x40, 0x08, 0x52, 0x3F, 0x06, 0x5B,
		0x4F, 0x66, 0x6D, 0x7D, 0x27, 0x7F, 0x6F, 0x09, 0x0D, 0x46, 0x48, 0x70, 0x53, 0x7B, 0x77, 0x7C, 0x39, 0x5E, 0x79,
		0x71, 0x3D, 0x76, 0x06, 0x1E, 0x75, 0x38, 0x2B, 0x37, 0x3F, 0x73, 0x67, 0x31, 0x6D, 0x07, 0x3E, 0x6A, 0x7E, 0x49,
		0x6E, 0x5B, 0x39, 0x64, 0x0F, 0x23, 0x08, 0x60, 0x5F, 0x7C, 0x58, 0x5E, 0x7B, 0x71, 0x6F, 0x74, 0x05, 0x0E, 0x75,
		0x06, 0x55, 0x54, 0x5C, 0x73, 0x67, 0x50, 0x6D, 0x78, 0x1C, 0x1D, 0x7E, 0x48, 0x6E, 0x5B, 0x46, 0x30, 0x70, 0x01
	]
	for i in range(32, 127):
		write(i)
		test_equal(read(), expected[i - 32])
	# BCD Mode
	set_mode(BCD_ONES)
	expected = [0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x27, 0x7F, 0x6F]
	for i in range(10):
		write(i)
		test_equal(read(), expected[i])
	# Print Report
	print(f"Passed: {passed} / {passed + failed} \tFailed: {failed} / {passed + failed}")

def display_test(delay=500):
	init()
	set_display_on(True)
	while True:
		# BCD Mode
		set_bi(0) # blank during mode switch
		set_mode(BCD_ONES)
		for v in range(1, 8):
			set_bcd_variant(v)
			for i in range(0, 16):
				write(i)
				set_bi(1)
				time.sleep_ms(delay)
		# ASCII Mode
		set_bi(0) # blank during mode switch
		set_mode(ASCII)
		for i in range(32, 128):
			write(i)
			set_bi(1)
			time.sleep_ms(delay)
		# Cistercian Mode
		set_bi(0) # blank during mode switch
		set_mode(CIS_ONES)
		for i in range(0, 16):
			write(i)
			set_bi(1)
			time.sleep_ms(delay)
		# Kaktovik Mode
		set_bi(0) # blank during mode switch
		set_mode(KAKTOVIK)
		for i in range(0, 32):
			write(i)
			set_bi(1)
			time.sleep_ms(delay)

def display_message(message='HELLO TINY TAPEOUT', delay=500):
	init()
	set_mode(ASCII)
	set_display_on(True)
	for ch in message:
		write(ord(ch))
		time.sleep_ms(delay)
	set_display_on(False)
	write(0)
