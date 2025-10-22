module nano20k_top(
    input sys_clk,
    input sys_reset,
    // LEDs
    output [5:0] led,
    // UART
    input UART_RXD,
    output UART_TXD,
    // SPI flash
    output flash_spi_cs_n,          // chip select
    input flash_spi_miso,           // master in slave out
    output flash_spi_mosi,          // mster out slave in
    output flash_spi_clk,           // spi clock
    output flash_spi_wp_n,          // write protect
    output flash_spi_hold_n         // hold operations
);

tinyQV_top i_tiniyQV(
        .clk(sys_clk),
        .rst_n(~sys_reset),
        .UART_RXD(UART_RXD),
        .UART_TXD(UART_TXD),
        .flash_spi_cs_n(flash_spi_cs_n),
        .flash_spi_miso(flash_spi_miso),
        .flash_spi_mosi(flash_spi_mosi),
        .flash_spi_clk(flash_spi_clk),
        .flash_spi_wp_n(flash_spi_wp_n),
        .flash_spi_hold_n(flash_spi_hold_n)
);


endmodule
