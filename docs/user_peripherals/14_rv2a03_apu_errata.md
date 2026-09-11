# RV2A03 NES APU Silicon Errata & WAV Glitch Analysis

**Target Chip**: TinyQV Sky25a Berzerk Shuttle (`ttsky25a-tinyQV-fjpolo-rv2a03`)  
**Peripheral Slot**: Slot 14 (`tqvp_fjpolo_rv2a03`)  
**Silicon Status**: **Taped Out (Frozen RTL)**  
**Document Purpose**: Document hardware errata present in the taped-out ASIC silicon, explain observed waveform anomalies in audio export/Audacity, provide register-level RTL fixes for future tapeouts/FPGA implementations, and define software/hardware workarounds for the physical silicon EVK.

---

## 1. Executive Summary & Audacity Glitch Breakdown

When inspecting the generated simulation audio (`rv2a03_audio.wav`) in an audio editor such as Audacity, severe visual glitches and distortion are present:

### Observed Waveform Features
1. **High DC Plateau (+22,000)**: Preceding the glitch, a flat DC plateau lasts ~79.3 ms.
2. **Severe Step Transition & Glitch (Circled in Yellow)**: A sharp transition spikes down through intermediate levels to a low DC rail.
3. **Negative DC Plateau (-18,000)**: Following the glitch, a flat DC rail persists for ~472.2 ms.
4. **Square "Teeth" on Triangle Wave Peaks**: On the right, the triangle wave displays square notches/steps on its peaks and slopes.

### Physical Breakdown Across Simulation Timeline

| Time Window | Audio Sample Range | Raw Hardware Value (`raw_s`) | Normalized WAV Value | Cause in Silicon & Testbench |
|:---|:---|:---|:---|:---|
| **0.0 - 154.8 ms** | 0 - 3,413 | 15 (DC leak) | +2,000 | SoC reset & boot string UART transmission. Triangle channel is disabled, but leaks DC 15 into mixer. |
| **154.8 - 369.8 ms** | 3,413 - 8,154 | 15 to 18 | +2,000 to +8,000 | Test 1 (Square 1) pulses superimposed on Triangle's DC 15 offset. |
| **369.8 - 941.6 ms** | 8,154 - 20,762 | 15 (DC leak) | +2,000 | Tests 2 & 3 execute; long delays caused by UART `printf` strings while Triangle leaks DC 15. |
| **941.6 - 1,020.9 ms** | 20,762 - 22,511 | **25 (DC leak)** | **+22,000** | **Test 4 (Noise)** completes. Channel muted in software (`$4015=0`), but Noise holds volume 15 for 79 ms due to slow clock gating. Leaks $40 + 60 = 100$ ($100 \gg 2 = 25$). |
| **1,020.9 - 1,049.6 ms** | 22,511 - 23,143 | 28 $\rightarrow$ 3 $\rightarrow$ 5 | **+28,000 to -22,000** | **Test 5 (All Channels)** runs briefly and is muted. Channels stop at arbitrary phase angles. |
| **1,049.6 - 1,521.8 ms** | 23,143 - 33,556 | **5 (DC leak)** | **-18,000** | CPU prints test summary and demo announcement over UART (472 ms). Triangle is frozen at step 5 indefinitely. |
| **1,521.8 - 1,660.0 ms** | 33,556 - 36,603 | 0 to 17 | -28,000 to +6,000 | Chiptune demo runs. Square 1 + Triangle play simultaneously, creating stepped notches on peaks. |

---

## 2. Hardware Errata in Taped-Out Silicon

### Errata #1: Triangle Channel Unmuted DC Leak & Missing Gating
- **Affected File**: `src/user_peripherals/RV2A03/apu.v`
- **Line**: 265
- **Current Taped-Out RTL**:
  ```verilog
  assign Sample = (applied_period > 1 || allow_us) ? (SeqPos[3:0] ^ {4{~SeqPos[4]}}) : sample_latch;
  ```
- **Root Cause**:
  `TriangleChan` has **no gating** on `Enabled`, `lc` (length counter), or `LinCtrZero` (linear counter zero flag).
  - At chip power-on reset, `SeqPos = 5'b00000`.
  - The sample formula evaluates to `4'b0000 ^ 4'b1111 = 4'b1111 = 15`.
  - In `APUMixer`, triangle is multiplied by 4:
    ```verilog
    wire [17:0] mixed_sum = {14'b0, square1} + {14'b0, square2} + {12'b0, triangle, 2'b0} + {12'b0, noise_lut[noise]};
    assign sample = mixed_sum[17:2];
    ```
    Triangle injects $15 \times 4 = 60$ into `mixed_sum`, causing an idle DC output of $60 \gg 2 = 15$ on the 16-bit audio output even before the channel is ever turned on!
  - When `rv2a03_mute()` or `$4015 = 0` is written, the sequencer stops advancing, but `Sample` **continues to output whatever value the sequencer stopped on** (in this test, step 5).
- **Silicon Impact**:
  Whenever Triangle is silenced or the APU is muted, the chip outputs a static DC offset of up to 15. In direct DC-coupled audio setups, this creates severe loud pops on note onset/cutoff and biases the speaker coil or amplifier input.

---

### Errata #2: Noise Channel Delayed Mute & Envelope Leak
- **Affected File**: `src/user_peripherals/RV2A03/apu.v`
- **Line**: 371
- **Current Taped-Out RTL**:
  ```verilog
  assign Sample = (~lc || Shift[14]) ? 4'd0 : Envelope;
  ```
- **Root Cause**:
  `NoiseChan` does **not** check `~Enabled` directly in its output assignment. It relies solely on `~lc` (length counter active).
  In `LenCounterUnit`:
  ```verilog
  always_ff @(posedge clk) begin : lenunit
      if (aclk1_d)
          if (~enabled)
              lc_on <= 0;
  ```
  `lc_on` is only updated when `aclk1_d` pulses. `aclk1_d` is derived from the APU frame counter (~240 Hz). Furthermore, when `halt_in` (`loop_env` / halt bit) is set to 1 (as is common for sound effects and music), `len_counter_int` is halted.
  If the LFSR shift register bit `Shift[14]` happens to stop on 0 when muted, and `aclk1_d` has not cleared `lc_on`, `Sample` continuously outputs `Envelope` (volume 15 = LUT value 40).
- **Silicon Impact**:
  After disabling the noise channel via register `$4015`, the noise channel continues to output static volume for up to 79+ ms, resulting in the high plateau (+22,000 in WAV) during UART delays.

---

### Errata #3: Square Channels Delayed Mute via `lc`
- **Affected File**: `src/user_peripherals/RV2A03/apu.v`
- **Line**: 157
- **Current Taped-Out RTL**:
  ```verilog
  assign Sample = (~lc | ~ValidFreq | ~DutyEnabledUsed) ? 4'd0 : Envelope;
  ```
- **Root Cause**:
  Similar to the noise channel, `SquareChan` does not gate directly on `~Enabled`. When `$4015` is cleared, the channel only mutes when `~DutyEnabledUsed` is high (during the inactive duty cycle phase) or once `lc` is deasserted. If the square sequencer stops on an active duty step, it may leak until the next clock event.

---

### Errata #4: Testbench Midpoint Centering Artifact (Simulation Only)
- **Affected File**: `test/test_rv2a03_test.py`
- **Lines**: 17–30
- **Current Python Logic**:
  ```python
  center = (min_val + max_val) / 2.0
  span = (max_val - min_val) / 2.0
  for s in samples:
      norm = int(((s - center) / span) * 28000)
  ```
- **Root Cause**:
  The APU hardware produces unipolar samples `[0..28]`. In `save_wav()`, `min_val` was 0 and `max_val` was 28, producing `center = 14`.
  - True hardware silence (`sample = 0`) was mapped to:
    $$\text{norm} = \frac{0 - 14}{14} \times 28000 = -28000$$
  - Idle Triangle leak (`sample = 15`) was mapped to:
    $$\text{norm} = \frac{15 - 14}{14} \times 28000 = +2000$$
  - Idle Noise leak (`sample = 25`) was mapped to:
    $$\text{norm} = \frac{25 - 14}{14} \times 28000 = +22000$$
  - Frozen Triangle after Test 5 (`sample = 5`) was mapped to:
    $$\text{norm} = \frac{5 - 14}{14} \times 28000 = -18000$$
  The testbench converted silent periods into artificial maximum-amplitude DC rails!

---

### Errata #5: Polyphonic Harmonic Summation in Musical Demo
- **Affected File**: `tinyQV-projects/rv2a03_test/main.c`
- **Lines**: 298–305
- **Explanation of "Teeth" on Triangle Peaks**:
  In `play_chiptune_demo()`:
  ```c
  rv2a03_enable_channels(RV2A03_STATUS_SQ1_ENABLE | RV2A03_STATUS_TRI_ENABLE);
  rv2a03_set_triangle(0x7F, true, tri_timer, 0x1E);
  // ...
  rv2a03_set_pulse1(RV2A03_DUTY_50, 0x0B, true, true, sq_timer, 0x1E);
  ```
  Both Square 1 (melody) and Triangle (bass) play simultaneously. Because `APUMixer` performs an arithmetic sum:
  $$\text{mixed\_sum} = \text{sq1} + \text{sq2} + (\text{triangle} \ll 2) + \text{noise\_lut}[\text{noise}]$$
  The 50% duty square wave rapidly toggles between 0 and 11 ($11 \gg 2 \approx +2$ to $+3$). When superimposed on the slow 32-step triangle wave, each peak and slope contains distinct square teeth with an amplitude of +2. This is **correct polyphonic behavior**, but looks like a glitch when expecting an isolated single-channel triangle test.

---

## 3. RTL Fixes for Future Silicon & FPGA Implementations

For future ASIC respins or FPGA targets (e.g. Sipeed Tang Nano 20K / Tang Mega 138K), the following edits completely eliminate DC leakage and delayed muting:

### Fix 1: Triangle Channel Immediate Gating
In `apu.v` (`TriangleChan`):
```verilog
// Before:
assign Sample = (applied_period > 1 || allow_us) ? (SeqPos[3:0] ^ {4{~SeqPos[4]}}) : sample_latch;

// Fix: Gate immediately on Enabled, lc, and LinCtrZero
assign Sample = (~Enabled | ~lc | LinCtrZero) ? 4'd0 :
                ((applied_period > 1 || allow_us) ? (SeqPos[3:0] ^ {4{~SeqPos[4]}}) : sample_latch);
```
And initialize `sample_latch` to 0 on reset:
```verilog
if (reset) begin
    sample_latch <= 4'd0; // Was 4'hF
    // ...
```

### Fix 2: Noise Channel Immediate Gating
In `apu.v` (`NoiseChan`):
```verilog
// Before:
assign Sample = (~lc || Shift[14]) ? 4'd0 : Envelope;

// Fix: Gate immediately on Enabled
assign Sample = (~Enabled | ~lc | Shift[14]) ? 4'd0 : Envelope;
```

### Fix 3: Square Channels Immediate Gating
In `apu.v` (`SquareChan`):
```verilog
// Before:
assign Sample = (~lc | ~ValidFreq | ~DutyEnabledUsed) ? 4'd0 : Envelope;

// Fix: Gate immediately on Enabled
assign Sample = (~Enabled | ~lc | ~ValidFreq | ~DutyEnabledUsed) ? 4'd0 : Envelope;
```

---

## 4. Mitigation & Workarounds for Taped-Out Silicon EVK

Because the physical ASIC cannot be changed, the following software and hardware engineering mitigations must be used with the EVK:

### A. Firmware Muting Procedure (Software Workaround)
In `rv2a03.c`, do **not** rely solely on writing `$4015 = 0x00`. Always zero out individual channel volume registers before disabling the status register:

```c
void rv2a03_mute_safe(void) {
    // 1. Force Pulse 1 & Pulse 2 volume to 0 (envelope disable + vol 0)
    rv2a03_write_reg(RV2A03_REG_SQ1_VOL, 0x30);
    rv2a03_write_reg(RV2A03_REG_SQ2_VOL, 0x30);

    // 2. Clear Triangle linear counter and length counter
    rv2a03_write_reg(RV2A03_REG_TRI_LINEAR, 0x00);
    rv2a03_write_reg(RV2A03_REG_TRI_HI, 0x00);

    // 3. Force Noise volume to 0
    rv2a03_write_reg(RV2A03_REG_NOISE_VOL, 0x30);
    rv2a03_write_reg(RV2A03_REG_NOISE_HI, 0x00);

    // 4. Disable all channels in status register
    rv2a03_write_reg(RV2A03_REG_STATUS, 0x00);
}
```

### B. Board-Level Hardware Mitigation (EVK Audio Output)
1. **Series AC-Coupling Capacitor**:
   Always place a **$10\,\mu\text{F}$ to $47\,\mu\text{F}$ non-polarized or electrolytic capacitor** in series with the analog DAC/PWM audio pin before feeding the speaker amplifier (e.g. MAX98357A / PAM8403 / 3.5mm jack).
   - This physically blocks all DC offsets ($0\text{ Hz}$), removing the static offset of 15 and preventing amplifier input saturation or speaker coil heating.
2. **First-Order RC High-Pass Filter**:
   Pair the capacitor with a $10\,\text{k}\Omega$ pulldown resistor to ground:
   $$f_c = \frac{1}{2\pi R C} = \frac{1}{2\pi \times 10{,}000\,\Omega \times 10 \times 10^{-6}\,\text{F}} \approx 1.59\,\text{Hz}$$
   This completely removes audible pops when switching between active audio and idle CPU periods.

### C. Testbench Audio Export Fix (`test_rv2a03_test.py`)
In the simulation testbench, replace the midpoint calculation with a digital 1st-order DC-blocking high-pass filter ($y[n] = x[n] - x[n-1] + R \cdot y[n-1]$, with $R = 0.995$):

```python
def save_wav(filename, samples, sample_rate=22050):
    if not samples:
        return

    # Digital DC-blocking filter simulating board-level AC coupling
    R = 0.995
    filtered = []
    y = 0.0
    prev_x = float(samples[0])
    for s in samples:
        x = float(s)
        y = x - prev_x + R * y
        prev_x = x
        filtered.append(y)

    max_val = max(abs(f) for f in filtered) or 1.0
    scale = 28000.0 / max_val

    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        raw_bytes = bytearray()
        for f in filtered:
            norm = int(f * scale)
            norm = max(-32767, min(32767, norm))
            raw_bytes.extend(struct.pack('<h', norm))
        wav_file.writeframes(raw_bytes)
```
- True silence cleanly settles to **0** (the center horizontal line in Audacity).
- DC offset plateaus (+22,000 / -18,000) are eliminated.
- AC audio waveforms swing symmetrically around 0.
