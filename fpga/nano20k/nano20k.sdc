// SDC File for tinyQV_top (27 MHz Clock)

// 1. Primary Clock Definition
// The clock frequency is 27 MHz (Period: 37.037 ns).

// Define the main system clock
create_clock -name CLK_MAIN -period 37.04 [get_nets {clk}]       // 27 Mhz

// Account for clock uncertainty (jitter, phase error - conservative 5% of period)
set_clock_uncertainty 1.85 -setup -from [get_clocks {CLK_MAIN}]