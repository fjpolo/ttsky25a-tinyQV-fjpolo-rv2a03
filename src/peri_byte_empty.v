/*
 * Copyright (c) 2025 Michael Bell
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

// A TinyQV byte peripheral that does nothing
module tqvp_byte_empty (
    input wire         clk,
    input wire         rst_n,

    input wire  [7:0]  ui_in,        // The input PMOD, always available
    output wire [7:0]  uo_out,       // The output PMOD.  Each wire is only connected if this peripheral is selected

    input wire [3:0]   address,      // Address within this peripheral's address space

    input wire         data_write,   // Data write request from the TinyQV core.
    input wire [7:0]   data_in,      // Data in to the peripheral, valid when data_write is high.
    
    output wire [7:0]  data_out      // Data out from the peripheral, set this in accordance with the supplied address
);

    // All output pins must be assigned. If not used, assign to 0.
    assign uo_out = 0;
    assign data_out = 8'h0;

    // List all unused inputs to prevent warnings
    wire _unused = &{clk, rst_n, ui_in, address, data_in, data_write, 1'b0};

endmodule
