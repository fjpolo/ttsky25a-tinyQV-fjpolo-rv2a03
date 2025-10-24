/* Copyright 2023-2024 (c) Michael Bell
   SPDX-License-Identifier: Apache-2.0
 */

module sim_qspi (
    // External SPI interface
    input wire      [3:0] qspi_data_in,
    output reg [3:0] qspi_data_out,
    input wire            qspi_clk,

    input wire qspi_flash_select,
    input wire qspi_ram_a_select,
    input wire qspi_ram_b_select
);

    // --- CONFIGURATION PARAMETERS ---
    // ROM and RAM size in bytes is 1 << XXX_BITS.
    // 2KB ROM (2^11) and 1KB RAMs (2^10)
    localparam   ROM_BITS       = 11; 
    localparam   RAM_A_BITS     = 10;
    localparam   RAM_B_BITS     = 10;

    // --- BRAM INFERENCE AND INITIALIZATION ---
    // These large arrays will be inferred as BRAM by the Gowin toolchain.
    // Dimensions match the calculated size: (2^N)
    reg [7:0] rom_mem   [(1<<ROM_BITS) - 1:0] /*synthesis syn_ramstyle="block_ram"*/;
    reg [7:0] ram_a_mem [(1<<RAM_A_BITS) - 1:0] /*synthesis syn_ramstyle="block_ram"*/;
    reg [7:0] ram_b_mem [(1<<RAM_B_BITS) - 1:0] /*synthesis syn_ramstyle="block_ram"*/;

    // ROM Initialization
    initial begin
        // CRITICAL: Ensure 'program.hex' is your byte-per-line Risc-V program output
        // and is placed in the project root directory where the compiler can find it.
        $readmemh("program.hex", rom_mem);
        
        // Note: For simulation, you might want to initialize RAM to known values.
        // For FPGA implementation, RAM is usually initialized in the linker script (by .bss and .data copy).
        // $readmemh("ram_init.hex", ram_a_mem);
        // $readmemh("ram_init.hex", ram_b_mem);
    end
    
    // Wires for BRAM read data - direct array access
    // The address index is the 8-bit word address (addr[N:1])
    wire [7:0] rom_buff_out   = rom_mem[addr[ROM_BITS:1]]; 
    reg [7:0] ram_a_buff_out;
    reg [7:0] ram_b_buff_out;

    // --- End BRAM Inference ---

    reg [31:0] cmd;
    reg [24:0] addr;
    reg [5:0] start_count;
    reg reading_dummy;
    reg reading;
    reg writing;
    reg error;
    reg [3:0] data_buff_in;
    
    wire any_select = qspi_flash_select && qspi_ram_a_select && qspi_ram_b_select;

    // --- RAM Read Logic ---
    always @(posedge qspi_clk)
        ram_a_buff_out = ram_a_mem[addr[RAM_A_BITS:1]];

    always @(posedge qspi_clk)
        ram_b_buff_out = ram_b_mem[addr[RAM_A_BITS:1]];

    // --- RAM Write Logic (Direct array write) ---
    // This logic handles the 8-bit write (combined high/low nibbles) across two clock half-cycles
    // Write to RAM A
    wire ramA_write = ((writing)&&(addr[0])&&(!qspi_ram_a_select));
    always @(posedge qspi_clk) begin
        if (ramA_write)
            // Write to RAM A: High nibble (data_buff_in) and Low nibble (qspi_data_in)
            ram_a_mem[addr[RAM_A_BITS:1]] <= {data_buff_in, qspi_data_in};
    end

    // Write to RAM B
    wire ramB_write = ((writing)&&(addr[0])&&(!qspi_ram_b_select));
    always @(posedge qspi_clk) begin
        if (ramB_write)
            ram_b_mem[addr[RAM_B_BITS:1]] <= {data_buff_in, qspi_data_in};
    end

    wire [5:0] next_start_count = start_count + 1;

    // Command/State Machine Logic (Posedge Clock)
    always @(posedge qspi_clk or posedge any_select) begin
        if (any_select) begin
            cmd <= 0;
            start_count <= 0;
        end else begin
            start_count <= next_start_count;

            // Capture the first nibble of an 8-bit word when addr[0] is low
            if (!addr[0]) data_buff_in <= qspi_data_in;

            // Shift in command until reading/writing starts
            if (!reading && !writing && !error) begin
                cmd <= {cmd[27:0], qspi_data_in};
            end
        end
    end

    // Address/State Machine Logic (Negedge Clock)
    always @(negedge qspi_clk or posedge any_select) begin
        if (any_select) begin
            reading <= 0;
            reading_dummy <= 0;
            writing <= 0;
            error <= 0;
            addr <= 0;
        end else begin
            if (reading || writing) begin
                // Increment address for data transfer
                addr <= addr + 1;
            end else if (reading_dummy) begin
                // Handle dummy cycles for QSPI Flash (Opcode 0x0B)
                if (start_count < 8 && cmd[3:0] != 4'b1010) begin
                    error <= 1;
                    reading_dummy <= 0;
                end
                if (start_count == 12) begin
                    reading <= 1;
                    reading_dummy <= 0;
                end
            end else if (!error && start_count == (qspi_flash_select ? 8 : 6)) begin
                // Command finished, set initial read/write state
                addr[ROM_BITS:1] <= cmd[ROM_BITS-1:0]; // Initialize Word Address
                addr[0] <= 0;
                if (!qspi_flash_select || cmd[31:24] == 8'h0B)
                    // QSPI Flash Read (0x0B) or RAM Read (default)
                    reading_dummy <= 1;
                else if (cmd[31:24] == 8'h02)
                    // QSPI Flash Write (0x02)
                    writing <= 1;
                else
                    // Unrecognized command
                    error <= 1;
            end
        end
    end

    // Data Output Logic (Negedge Clock)
    always @(negedge qspi_clk) begin
        // Determine which memory is selected and whether to output the high or low nibble (based on addr[0])
        qspi_data_out <= !qspi_ram_a_select ? (addr[0] ? ram_a_buff_out[3:0] : ram_a_buff_out[7:4]) :
                         !qspi_ram_b_select ? (addr[0] ? ram_b_buff_out[3:0] : ram_b_buff_out[7:4]) :
                                              (addr[0] ? rom_buff_out[3:0] : rom_buff_out[7:4]);
    end

endmodule
