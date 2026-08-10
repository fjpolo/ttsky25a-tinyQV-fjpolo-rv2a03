# SPDX-License-Identifier: Apache-2.0
# Author: Rebecca G. Bettencourt

# To use:
# 1. Run the test() function to verify that the peripheral is working correctly:
#    mpremote <port> run 37_intercal_alu.py exec 'test()'
# 2. Import as a library to use the and16(), and32(), or16(), or32(),
#    xor16(), xor32(), mingle16(), select16(), and select32() functions.

import machine
import time
import tinyqv

# Hardware Implementation of INTERCAL Operators

PERIPHERAL_NUM = 37
BASE = tinyqv.get_base_address(PERIPHERAL_NUM)

def and16(a):
	machine.mem16[BASE] = a
	return machine.mem16[BASE+0x08] & 0xFFFF

def and32(a):
	machine.mem32[BASE] = a
	return machine.mem32[BASE+0x0C] & 0xFFFFFFFF

def or16(a):
	machine.mem16[BASE] = a
	return machine.mem16[BASE+0x10] & 0xFFFF

def or32(a):
	machine.mem32[BASE] = a
	return machine.mem32[BASE+0x14] & 0xFFFFFFFF

def xor16(a):
	machine.mem16[BASE] = a
	return machine.mem16[BASE+0x18] & 0xFFFF

def xor32(a):
	machine.mem32[BASE] = a
	return machine.mem32[BASE+0x1C] & 0xFFFFFFFF

def mingle16(a, b):
	machine.mem16[BASE] = a
	machine.mem16[BASE+4] = b
	return machine.mem32[BASE+0x20] & 0xFFFFFFFF

def select16(a, b):
	machine.mem16[BASE] = a
	machine.mem16[BASE+4] = b
	return machine.mem16[BASE+0x28] & 0xFFFF

def select32(a, b):
	machine.mem32[BASE] = a
	machine.mem32[BASE+4] = b
	return machine.mem32[BASE+0x2C] & 0xFFFFFFFF

# Software Implementation of INTERCAL Operators

def soft_and16(a):
	return (((a & 1) << 15) | ((a >> 1) & 0x7FFF)) & a

def soft_and32(a):
	return (((a & 1) << 31) | ((a >> 1) & 0x7FFFFFFF)) & a

def soft_or16(a):
	return (((a & 1) << 15) | ((a >> 1) & 0x7FFF)) | a

def soft_or32(a):
	return (((a & 1) << 31) | ((a >> 1) & 0x7FFFFFFF)) | a

def soft_xor16(a):
	return (((a & 1) << 15) | ((a >> 1) & 0x7FFF)) ^ a

def soft_xor32(a):
	return (((a & 1) << 31) | ((a >> 1) & 0x7FFFFFFF)) ^ a

def soft_mingle16(a, b):
	c = 0
	db = 1
	sb = 1
	for i in range(16):
		if (b & sb):
			c |= db
		db <<= 1
		if (a & sb):
			c |= db
		db <<= 1
		sb <<= 1
	return c

def soft_select16(a, b):
	c = 0
	db = 1
	sb = 1
	for i in range(16):
		if (b & sb):
			if (a & sb):
				c |= db
			db <<= 1
		sb <<= 1
	return c

def soft_select32(a, b):
	c = 0
	db = 1
	sb = 1
	for i in range(32):
		if (b & sb):
			if (a & sb):
				c |= db
			db <<= 1
		sb <<= 1
	return c

# Tests for Speed and Correctness

class LFSR():
	def __init__(self, seed):
		self.seed = seed

	def step(self):
		bit = self.seed & 1
		bit ^= (self.seed >> 1) & 1
		bit ^= (self.seed >> 3) & 1
		bit ^= (self.seed >> 12) & 1
		self.seed >>= 1
		self.seed |= bit << 15
		return bit

	def rand(self, n):
		bits = 0
		for i in range(n):
			bits <<= 1
			bits |= self.step()
		return bits

def test_cases(seed, count):
	cases_a16 = [0] * count
	cases_b16 = [0] * count
	cases_a32 = [0] * count
	cases_b32 = [0] * count
	lfsr = LFSR(seed)
	for i in range(count):
		cases_a16[i] = lfsr.rand(16)
		cases_b16[i] = lfsr.rand(16)
		cases_a32[i] = lfsr.rand(32)
		cases_b32[i] = lfsr.rand(32)
	return (count, cases_a16, cases_b16, cases_a32, cases_b32)

def test_hardware(cases):
	count, cases_a16, cases_b16, cases_a32, cases_b32 = cases
	results_and16 = [0] * count
	results_and32 = [0] * count
	results_or16 = [0] * count
	results_or32 = [0] * count
	results_xor16 = [0] * count
	results_xor32 = [0] * count
	results_mingle16 = [0] * count
	results_select16 = [0] * count
	results_select32 = [0] * count
	start = time.ticks_us()
	for i in range(count):
		results_and16[i] = and16(cases_a16[i])
		results_and32[i] = and32(cases_a32[i])
		results_or16[i] = or16(cases_a16[i])
		results_or32[i] = or32(cases_a32[i])
		results_xor16[i] = xor16(cases_a16[i])
		results_xor32[i] = xor32(cases_a32[i])
		results_mingle16[i] = mingle16(cases_a16[i], cases_b16[i])
		results_select16[i] = select16(cases_a16[i], cases_b16[i])
		results_select32[i] = select32(cases_a32[i], cases_b32[i])
	stop = time.ticks_us()
	elapsed = time.ticks_diff(stop, start)
	results = (
		results_and16 + results_and32 +
		results_or16 + results_or32 +
		results_xor16 + results_xor32 +
		results_mingle16 +
		results_select16 +
		results_select32
	)
	return (elapsed, results)

def test_software(cases):
	count, cases_a16, cases_b16, cases_a32, cases_b32 = cases
	results_and16 = [0] * count
	results_and32 = [0] * count
	results_or16 = [0] * count
	results_or32 = [0] * count
	results_xor16 = [0] * count
	results_xor32 = [0] * count
	results_mingle16 = [0] * count
	results_select16 = [0] * count
	results_select32 = [0] * count
	start = time.ticks_us()
	for i in range(count):
		results_and16[i] = soft_and16(cases_a16[i])
		results_and32[i] = soft_and32(cases_a32[i])
		results_or16[i] = soft_or16(cases_a16[i])
		results_or32[i] = soft_or32(cases_a32[i])
		results_xor16[i] = soft_xor16(cases_a16[i])
		results_xor32[i] = soft_xor32(cases_a32[i])
		results_mingle16[i] = soft_mingle16(cases_a16[i], cases_b16[i])
		results_select16[i] = soft_select16(cases_a16[i], cases_b16[i])
		results_select32[i] = soft_select32(cases_a32[i], cases_b32[i])
	stop = time.ticks_us()
	elapsed = time.ticks_diff(stop, start)
	results = (
		results_and16 + results_and32 +
		results_or16 + results_or32 +
		results_xor16 + results_xor32 +
		results_mingle16 +
		results_select16 +
		results_select32
	)
	return (elapsed, results)

def test_equal(results1, results2):
	passed = 0
	failed = 0
	count = max(len(results1), len(results2))
	for i in range(count):
		if results1[i] == results2[i]:
			passed += 1
		else:
			failed += 1
	return (passed, failed, count)

def test_batch(seed, count):
	cases = test_cases(seed, count)
	hw_elapsed, hw_results = test_hardware(cases)
	sw_elapsed, sw_results = test_software(cases)
	passed, failed, count = test_equal(hw_results, sw_results)
	print(f"Passed: {passed} / {count} \tFailed: {failed} / {count}")
	print(f"HW Elapsed: {hw_elapsed} us = {len(hw_results) * 1000000 / hw_elapsed} FROPS (frivolous operations per second)")
	print(f"SW Elapsed: {sw_elapsed} us = {len(sw_results) * 1000000 / sw_elapsed} FROPS (frivolous operations per second)")

def test(seed=0xACE1, batch_size=10, batch_count=10):
	if batch_count < 0:
		while True:
			test_batch(seed, batch_size)
			seed += 1
	else:
		for i in range(batch_count):
			test_batch(seed + i, batch_size)
