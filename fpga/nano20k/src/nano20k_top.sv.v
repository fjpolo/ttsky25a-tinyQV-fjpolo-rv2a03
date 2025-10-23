/*
 * Copyright (c) 2025 @fjpolo
 * SPDX-License-Identifier: Apache-2.0
 */

module nano20k_top(
    input sys_clk,
    input s1,
    input s2,
    // LEDs
    output [5:0] led,
    // UART
    input  UART_RXD,
    output UART_TXD,
    // SPI flash
    output flash_spi_cs_n,              // chip select
    input  flash_spi_miso,              // master in slave out
    output flash_spi_mosi,              // mster out slave in
    output flash_spi_clk,               // spi clock
    output flash_spi_wp_n,              // write protect
    output flash_spi_hold_n             // hold operations
);
wire sys_reset_n = ~(s1 | s2);

`ifndef TEST_LEDS
assign led[0] = ~UART_RXD; 
assign led[1] = ~UART_TXD; 
// assign led[0] = sys_clk; 
// assign led[1] = clk_64Mhz; 
`endif

wire clk_64Mhz;
// NOTE: Assuming your Gowin_rPLL is configured to output the desired 81MHz clock.
// The input must be the top-level clock: sys_clk
Gowin_rPLL pll_80k(
    .clkout(clk_64Mhz),
    .clkin(sys_clk)
    );

reg [7:0] portA;

tinyQV_top i_tiniyQV(
    .clk(clk_64Mhz),
    .rst_n(sys_reset_n),
    .uo_out(portA),
    .i_uart_rx(),
    .o_uart_tx()
);
assign UART_TXD = portA[0];
// assign led[1:0] = portA[1:0];

`ifdef TEST_LEDS
    reg [24:0] counter = 'h00;
    // Using sys_clk for blinking counter is often better for sanity check
    // but the final core must run on clk_64Mhz
    always @(posedge sys_clk) begin
        if(counter == 64_000_000) // Assuming sys_clk is 64MHz, this is 1 second
            counter = 'h00;
        else
            counter = counter + 1;
    end

    reg r_led_output = 1'b1;
    always @(posedge sys_clk) begin
        if(counter ==64_000_000)
            r_led_output = ~r_led_output;
    end
    
assign led[0] = r_led_output;
`endif

endmodule
