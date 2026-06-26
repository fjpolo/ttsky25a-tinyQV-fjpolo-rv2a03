# Micropython testing on TinyQV

Connect the QSPI Pmod to the BIDIR socket on the TinyTapeout demo board, and load the Micropython binary with [the programmer](https://program.tinyqv.com) by selecting it and clicking FLASH AND RUN.

A Micropython REPL should appear in a text box at the top of the page.

## First steps - GPIO

Try flashing the bottom segment on the seven segment display, by typing or copy-pasting the following:

    from machine import Pin

    out3 = Pin(3)
    out3.on()
    out3.off()

`Pin(n)` with no extra arguments and n from 0-7 will initialize the output pin for general purpose IO use, meaning you can set it high or low using `on()` and `off()`, or equivalently `value(0)` and `value(1)` methods.

Don't use `Pin(0)` as that is used by the UART to send data to the Micropython REPL.

## Assigning output pins to peripherals

This is the [list of peripherals](../docs/info.md#contributed-peripherals) on TinyQV "Asteroids".  Many of them are able to transmit data on the output pins.  Only one peripheral can be in control of an output pin at any one time.  To select which, use e.g.:

    Pin(2, func_sel=21)

to set out2 to be controlled by Matt's PWM peripheral.

## Reading and writing peripheral registers

The tinyqv module provides access functions for the peripheral registers.  For example, to set register at address 1 on the PWM peripheral to 100:

    import tinyqv
    tinyqv.write_byte_reg(21, 1, 100)

The functions are named:

- `read_byte_reg(peripheral_num, address)` read a byte register
- `write_byte_reg(peripheral_num, address, value)` write `value` to a byte register
- `read_hword_reg(peripheral_num, address)` read a half-word (16 bit) register
- `write_hword_reg(peripheral_num, address, value)` write `value` to a half-word (16 bit) register
- `read_word_reg(peripheral_num, address)` read a word (32 bit) register
- `write_word_reg(peripheral_num, address, value)` write `value` to a word (32 bit) register

## Reading input pins

The input pins in0-in7 have pin numbers 8-15 in Micropython.  So for example:

    from machine import Pin

    print(Pin(9).value())

Will print 0 or 1 depending on whether in1 reads low or high.

## Pasting larger amounts of code

You can go into "paste mode" at the Micropython into the REPL by pressing Ctrl-E.  This ensures formatting is preserved during the paste.  Press Ctrl-D to exit paste mode, the pasted code will be interpreted when you press Ctrl-D.

## Tests

See the python tests in this directory for tests of some peripherals.  Note that some of this code has not yet been tested 