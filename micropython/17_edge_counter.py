# SPDX-License-Identifier: Apache-2.0
# Author: Uri Shaked

# To use:
# 1. Run the auto_test() function to verify that the peripheral is working correctly.
# 2. Run the display_counter_test() function to display the counter value on the
#    7-segment display. It will count from 0 to F, with a 1 second delay between each value. 
#    This will disrupt the serial console output.

import machine
from machine import Pin
import time

PERIPHERAL_NUM = 17
BASE_ADDRESS = 0x800_0400 + (PERIPHERAL_NUM - 16) * 0x10
REG_RESET = 0
REG_INC = 1
REG_VALUE = 2
REG_CFG = 3
REG_PINS = 4

def write_reg(idx: int, value: int):
      machine.mem8[BASE_ADDRESS + idx] = value

def read_reg(idx: int) -> int:
      return machine.mem8[BASE_ADDRESS + idx]

def auto_test():
      """
      Basic test of the peripheral. Resets it, increments it, and checks the value.
      """

      write_reg(REG_RESET, 1)
      assert read_reg(REG_VALUE) == 0, "Peripheral did not reset to 0"

      write_reg(REG_INC, 1)
      assert read_reg(REG_VALUE) == 1, "Peripheral did not increment to 1"

      write_reg(REG_INC, 1)
      assert read_reg(REG_VALUE) == 2, "Peripheral did not increment to 2"

      write_reg(REG_VALUE, 42)
      assert read_reg(REG_VALUE) == 42, "Peripheral did not set value to 42"

      write_reg(REG_RESET, 1)
      assert read_reg(REG_VALUE) == 0, "Peripheral did not reset to 0"

      return "All tests passed!"

def set_display_on(enable: bool):
      """
      Configures the peripheral to output to the 7-segment display.
      """
      for i in range(8):
            Pin(i, func_sel=PERIPHERAL_NUM if enable else 0)
      if not enable:
            Pin(0, func_sel=2) # UART TX

def display_counter_test():
      """
      Displays the current value of the counter on the 7-segment display.
      This disrupts the serial console output.
      """
      set_display_on(True)
      for i in range(16):
            write_reg(REG_VALUE, i)
            time.sleep(1)
      set_display_on(False)
