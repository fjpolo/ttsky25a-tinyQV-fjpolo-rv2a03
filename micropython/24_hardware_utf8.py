# SPDX-License-Identifier: Apache-2.0
# Author: Rebecca G. Bettencourt

# To use:
# 1. Run the test() function to verify that the peripheral is working correctly:
#    mpremote <port> run 24_hardware_utf8.py exec 'test()'
# 2. Import as a library to use the utf_to_codepoints() and codepoints_to_utf()
#    functions. Or, have even more fun using the lower-level functions.

import machine
import tinyqv

PERIPHERAL_NUM = 24
BASE = tinyqv.get_base_address(PERIPHERAL_NUM)

# Error Flags
READY     = 0x01
RETRY     = 0x02
INVALID   = 0x04
OVERLONG  = 0x08
NONUNI    = 0x10
ERROR     = 0x20

# Property Flags
NORMAL    = 0x01
CONTROL   = 0x02
SURROGATE = 0x04
HIGHCHAR  = 0x08
PRIVATE   = 0x10
NONCHAR   = 0x20

# Reset Flags
CHECK_RANGE = 0x04
BIG_ENDIAN  = 0x08

reset_flags = -1

def set_check_range(chk):
	global reset_flags
	if chk:
		reset_flags |= CHECK_RANGE
	else:
		reset_flags &=~ CHECK_RANGE

def set_big_endian(cbe):
	global reset_flags
	if cbe:
		reset_flags |= BIG_ENDIAN
	else:
		reset_flags &=~ BIG_ENDIAN

def write_start():
	machine.mem8[BASE] = reset_flags

def write_utf32(b):
	machine.mem8[BASE+1] = b

def write_utf16(b):
	machine.mem8[BASE+2] = b

def write_utf8(b):
	machine.mem8[BASE+3] = b

def errors():
	return machine.mem8[BASE]

def properties():
	return machine.mem8[BASE+1]

def utf16_len():
	return machine.mem8[BASE+2] & 7

def utf16_eof():
	return machine.mem8[BASE+2] >> 7

def utf8_len():
	return machine.mem8[BASE+3] & 7

def utf8_eof():
	return machine.mem8[BASE+3] >> 7

def read_start():
	machine.mem8[BASE+4] = reset_flags

def read_utf32():
	machine.mem8[BASE+5] = 0
	return machine.mem8[BASE+5] & 0xFF

def read_utf16():
	machine.mem8[BASE+6] = 0
	return machine.mem8[BASE+6] & 0xFF

def read_utf8():
	machine.mem8[BASE+7] = 0
	return machine.mem8[BASE+7] & 0xFF

def get_rc():
	if (reset_flags & BIG_ENDIAN):
		rc = (machine.mem8[BASE+8] & 0xFF) << 24
		rc |= (machine.mem8[BASE+9] & 0xFF) << 16
		rc |= (machine.mem8[BASE+10] & 0xFF) << 8
		rc |= (machine.mem8[BASE+11] & 0xFF)
		return rc
	else:
		rc = (machine.mem8[BASE+8] & 0xFF)
		rc |= (machine.mem8[BASE+9] & 0xFF) << 8
		rc |= (machine.mem8[BASE+10] & 0xFF) << 16
		rc |= (machine.mem8[BASE+11] & 0xFF) << 24
		return rc

def set_rc(rc):
	if (reset_flags & BIG_ENDIAN):
		machine.mem8[BASE+8] = rc >> 24
		machine.mem8[BASE+9] = rc >> 16
		machine.mem8[BASE+10] = rc >> 8
		machine.mem8[BASE+11] = rc
	else:
		machine.mem8[BASE+8] = rc
		machine.mem8[BASE+9] = rc >> 8
		machine.mem8[BASE+10] = rc >> 16
		machine.mem8[BASE+11] = rc >> 24

# Code point used to report encoding error
REPLACEMENT_CHARACTER = 0xFFFD

def utf32_to_codepoints(b):
	i = 0
	n = len(b)
	c = []
	while i < n:
		write_start()
		write_utf32(b[i])
		write_utf32(b[i+1])
		write_utf32(b[i+2])
		write_utf32(b[i+3])
		i += 4
		e = errors()
		if (e & READY) and not (e & ERROR):
			# Valid UTF-32 character
			c.append(get_rc())
		else:
			# Invalid UTF-32 character
			c.append(REPLACEMENT_CHARACTER)
	return c

def utf16_to_codepoints(b):
	i = 0
	n = len(b)
	c = []
	while i < n:
		write_start()
		write_utf16(b[i])
		write_utf16(b[i+1])
		i += 2
		if (properties() & HIGHCHAR) and i < n:
			write_utf16(b[i])
			write_utf16(b[i+1])
			i += 2
		e = errors()
		if (e & READY) and not (e & ERROR):
			# Valid UTF-16 sequence
			c.append(get_rc())
		elif (e & RETRY):
			# Unpaired high surrogate
			c.append(get_rc())
			# Try previous word again as it was discarded
			i -= 2
		else:
			# Invalid UTF-16 sequence (should not happen)
			c.append(REPLACEMENT_CHARACTER)
	return c

def utf8_to_codepoints(b):
	i = 0
	n = len(b)
	c = []
	while i < n:
		write_start()
		while True:
			write_utf8(b[i])
			i += 1
			e = errors()
			if (e & READY) and not (e & ERROR):
				# Valid UTF-8 sequence
				c.append(get_rc())
				break
			elif (e & RETRY):
				# Truncated UTF-8 sequence
				c.append(REPLACEMENT_CHARACTER)
				# Try previous byte again as it was discarded
				i -= 1
				break
			elif e:
				# Invalid UTF-8 sequence
				c.append(REPLACEMENT_CHARACTER)
				break
			elif i < n:
				# Incomplete UTF-8 sequence
				continue
			else:
				# Truncated UTF-8 sequence
				c.append(REPLACEMENT_CHARACTER)
				break
	return c

def codepoints_to_utf32(c):
	b = []
	for rc in c:
		set_rc(rc)
		read_start()
		b.append(read_utf32())
		b.append(read_utf32())
		b.append(read_utf32())
		b.append(read_utf32())
	return bytes(b)

def codepoints_to_utf16(c):
	b = []
	for rc in c:
		set_rc(rc)
		read_start()
		while not utf16_eof():
			b.append(read_utf16())
	return bytes(b)

def codepoints_to_utf8(c):
	b = []
	for rc in c:
		set_rc(rc)
		read_start()
		while not utf8_eof():
			b.append(read_utf8())
	return bytes(b)

# Tests

def test_equal(actual, expected):
	if actual == expected:
		print('OK')
	else:
		print(f"NG: {actual} != {expected}")

def test():
	set_big_endian(False)

	utf32in = b'\x48\x00\x00\x00\x69\x00\x00\x00\xC0\x03\x00\x00\x3D\x20\x00\x00\x2D\x4E\x00\x00\xFF\xF8\x00\x00\x00\xF6\x01\x00\x6C\x19\x0F\x00\x56\x34\x12\x00\x98\xBA\xDC\xFE'
	utf32out = [0x48, 0x69, 0x3C0, 0x203D, 0x4E2D, 0xF8FF, 0x1F600, 0xF196C, 0xFFFD, 0xFFFD]
	test_equal(utf32_to_codepoints(utf32in), utf32out)

	utf16in = b'\x48\x00\x69\x00\xC0\x03\x3D\x20\x2D\x4E\xFF\xF8\x3D\xD8\x00\xDE\x86\xDB\x6C\xDD\x00\x00\x88\xD8\x00\x00\xCC\xDC\x00\x00'
	utf16out = [0x48, 0x69, 0x3C0, 0x203D, 0x4E2D, 0xF8FF, 0x1F600, 0xF196C, 0, 0xD888, 0, 0xDCCC, 0]
	test_equal(utf16_to_codepoints(utf16in), utf16out)

	utf8in = b'\x48\x69\xCF\x80\xE2\x80\xBD\xE4\xB8\xAD\xEF\xA3\xBF\xF0\x9F\x98\x80\xF3\xB1\xA5\xAC\x21\xF0\x9F\x21\xF0\x80\x81\x82\x21\xF4\xBF\xBE\xBD\x21\xF0\x9F'
	utf8out = [0x48, 0x69, 0x3C0, 0x203D, 0x4E2D, 0xF8FF, 0x1F600, 0xF196C, 33, 0xFFFD, 33, 0xFFFD, 33, 0xFFFD, 33, 0xFFFD]
	test_equal(utf8_to_codepoints(utf8in), utf8out)

	utf8in = b'\xED\xA2\x88\xED\xB3\x8C\x21\xFE\x21\xFF\x21'
	utf8out = [0xD888, 0xDCCC, 33, 0xFFFD, 33, 0xFFFD, 33]
	test_equal(utf8_to_codepoints(utf8in), utf8out)

	codepoints = [0x48, 0x69, 0x3C0, 0x203D, 0x4E2D, 0xF8FF, 0x1F600, 0xF196C, 0xD888, 0xDCCC]
	utf32out = b'\x48\x00\x00\x00\x69\x00\x00\x00\xC0\x03\x00\x00\x3D\x20\x00\x00\x2D\x4E\x00\x00\xFF\xF8\x00\x00\x00\xF6\x01\x00\x6C\x19\x0F\x00\x88\xD8\x00\x00\xCC\xDC\x00\x00'
	test_equal(codepoints_to_utf32(codepoints), utf32out)

	utf16out = b'\x48\x00\x69\x00\xC0\x03\x3D\x20\x2D\x4E\xFF\xF8\x3D\xD8\x00\xDE\x86\xDB\x6C\xDD\x88\xD8\xCC\xDC'
	test_equal(codepoints_to_utf16(codepoints), utf16out)

	utf8out = b'\x48\x69\xCF\x80\xE2\x80\xBD\xE4\xB8\xAD\xEF\xA3\xBF\xF0\x9F\x98\x80\xF3\xB1\xA5\xAC\xED\xA2\x88\xED\xB3\x8C'
	test_equal(codepoints_to_utf8(codepoints), utf8out)

	set_big_endian(True)

	utf32in = b'\x00\x00\x00\x48\x00\x00\x00\x69\x00\x00\x03\xC0\x00\x00\x20\x3D\x00\x00\x4E\x2D\x00\x00\xF8\xFF\x00\x01\xF6\x00\x00\x0F\x19\x6C\x00\x12\x34\x56\xFE\xDC\xBA\x98'
	utf32out = [0x48, 0x69, 0x3C0, 0x203D, 0x4E2D, 0xF8FF, 0x1F600, 0xF196C, 0xFFFD, 0xFFFD]
	test_equal(utf32_to_codepoints(utf32in), utf32out)

	utf16in = b'\x00\x48\x00\x69\x03\xC0\x20\x3D\x4E\x2D\xF8\xFF\xD8\x3D\xDE\x00\xDB\x86\xDD\x6C\x00\x00\xD8\x88\x00\x00\xDC\xCC\x00\x00'
	utf16out = [0x48, 0x69, 0x3C0, 0x203D, 0x4E2D, 0xF8FF, 0x1F600, 0xF196C, 0, 0xD888, 0, 0xDCCC, 0]
	test_equal(utf16_to_codepoints(utf16in), utf16out)

	utf8in = b'\x48\x69\xCF\x80\xE2\x80\xBD\xE4\xB8\xAD\xEF\xA3\xBF\xF0\x9F\x98\x80\xF3\xB1\xA5\xAC\x21\xF0\x9F\x21\xF0\x80\x81\x82\x21\xF4\xBF\xBE\xBD\x21\xF0\x9F'
	utf8out = [0x48, 0x69, 0x3C0, 0x203D, 0x4E2D, 0xF8FF, 0x1F600, 0xF196C, 33, 0xFFFD, 33, 0xFFFD, 33, 0xFFFD, 33, 0xFFFD]
	test_equal(utf8_to_codepoints(utf8in), utf8out)

	utf8in = b'\xED\xA2\x88\xED\xB3\x8C\x21\xFE\x21\xFF\x21'
	utf8out = [0xD888, 0xDCCC, 33, 0xFFFD, 33, 0xFFFD, 33]
	test_equal(utf8_to_codepoints(utf8in), utf8out)

	codepoints = [0x48, 0x69, 0x3C0, 0x203D, 0x4E2D, 0xF8FF, 0x1F600, 0xF196C, 0xD888, 0xDCCC]
	utf32out = b'\x00\x00\x00\x48\x00\x00\x00\x69\x00\x00\x03\xC0\x00\x00\x20\x3D\x00\x00\x4E\x2D\x00\x00\xF8\xFF\x00\x01\xF6\x00\x00\x0F\x19\x6C\x00\x00\xD8\x88\x00\x00\xDC\xCC'
	test_equal(codepoints_to_utf32(codepoints), utf32out)

	utf16out = b'\x00\x48\x00\x69\x03\xC0\x20\x3D\x4E\x2D\xF8\xFF\xD8\x3D\xDE\x00\xDB\x86\xDD\x6C\xD8\x88\xDC\xCC'
	test_equal(codepoints_to_utf16(codepoints), utf16out)

	utf8out = b'\x48\x69\xCF\x80\xE2\x80\xBD\xE4\xB8\xAD\xEF\xA3\xBF\xF0\x9F\x98\x80\xF3\xB1\xA5\xAC\xED\xA2\x88\xED\xB3\x8C'
	test_equal(codepoints_to_utf8(codepoints), utf8out)
