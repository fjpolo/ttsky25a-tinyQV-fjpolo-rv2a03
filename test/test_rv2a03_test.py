# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

import wave
import struct

from test_util import reset

def save_wav(filename, samples, sample_rate=22050):
    if not samples:
        return

    # In RV2A03, when the channels are playing, samples are unipolar positive (0 to ~32).
    # To avoid differentiator distortion (shark-fin decay) caused by high-pass filters,
    # we center active audio around its DC midpoint so square waves remain 100% flat
    # and triangle waves remain pure linear ramps.
    active_samples = [float(s) for s in samples if s != 0]
    mean_val = (sum(active_samples) / len(active_samples)) if active_samples else 0.0

    filtered = []
    for s in samples:
        if s == 0:
            filtered.append(0.0)
        else:
            filtered.append(float(s) - mean_val)

    max_val = max(abs(f) for f in filtered) or 1.0
    scale = 28000.0 / max_val

    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        raw_bytes = bytearray()
        for f in filtered:
            norm = int(round(f * scale))
            norm = max(-32767, min(32767, norm))
            raw_bytes.extend(struct.pack('<h', norm))
        wav_file.writeframes(raw_bytes)

async def read_char(dut, max_wait_cycles=100000, bit_cycles=4):
    for _ in range(max_wait_cycles):
        if dut.uart_tx.value == 0:
            break
        await ClockCycles(dut.clk, 1)
    else:
        return None

    # Wait to reach center of start bit (sample at cycle 2 for bit_cycles=4)
    await ClockCycles(dut.clk, bit_cycles // 2)
    assert dut.uart_tx.value == 0, f"Expected start bit 0, got {dut.uart_tx.value}"

    # Read 8 data bits
    uart_byte = 0
    for i in range(8):
        await ClockCycles(dut.clk, bit_cycles)
        uart_byte |= int(dut.uart_tx.value) << i

    # Wait for stop bit
    await ClockCycles(dut.clk, bit_cycles)
    assert dut.uart_tx.value == 1, f"Expected stop bit 1, got {dut.uart_tx.value}"

    return chr(uart_byte)

async def read_line(dut, max_wait_cycles=100000, bit_cycles=4):
    line = ""
    while True:
        ch = await read_char(dut, max_wait_cycles, bit_cycles)
        if ch is None:
            return line if line else None
        if ch == '\r':
            continue
        if ch == '\n':
            return line
        line += ch

@cocotb.test()
async def test_rv2a03_test(dut):
    dut._log.info("Starting RV2A03 Firmware SoC Simulation (Fast UART)...")

    clock = Clock(dut.clk, 15.624, units="ns")
    cocotb.start_soon(clock.start())

    # Reset CPU and QSPI flash controller (latency 1)
    await reset(dut, 1)

    # Audio sample capture
    audio_samples = []
    is_running = True
    is_demo = False

    async def record_audio():
        silent_count = 0
        while is_running:
            await ClockCycles(dut.clk, 64)
            try:
                val = int(dut.user_project.i_peripherals.i_user_peri14.apu_output_sample_16b.value)
                if val != 0 or is_demo:
                    audio_samples.append(val)
                    silent_count = 0
                elif silent_count < 20: # Keep short inter-test breath (20 samples) instead of 5,000
                    audio_samples.append(0)
                    silent_count += 1
            except Exception:
                pass

    cocotb.start_soon(record_audio())

    tests_passed = False
    fail_detected = False

    while True:
        line = await read_line(dut, max_wait_cycles=200000, bit_cycles=4)
        if line is None:
            dut._log.info("UART stream idle / completed.")
            break

        dut._log.info(f"[UART] {line}")

        if "Playing NES Chiptune Demo..." in line:
            is_demo = True
            dut._log.info(">>> Recording NES Chiptune Demo <<<")

        if "5/5 tests passed successfully" in line:
            tests_passed = True
            dut._log.info(">>> ALL 5 RV2A03 TESTS PASSED SUCCESSFULLY! <<<")

        if "Demo complete! APU muted." in line:
            dut._log.info(">>> CHIPTUNE DEMO COMPLETED SUCCESSFULLY! <<<")
            break

        if "FAIL" in line:
            fail_detected = True

    is_running = False
    if audio_samples:
        save_wav("rv2a03_audio.wav", audio_samples, sample_rate=22050)
        dut._log.info(f"[AUDIO] Exported {len(audio_samples)} samples to rv2a03_audio.wav (22.05 kHz)")

    assert not fail_detected, "RV2A03 firmware test reported a FAIL!"
    assert tests_passed, "Simulation finished without confirming 5/5 tests passed."
