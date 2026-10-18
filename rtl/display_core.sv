// X-ray - original challenge RTL, MIT license.
// 192x64 monochrome display; 16 pixels per word, 2 banks.
module display_core(
    input wire clk, input wire rst,
    output wire [9:0] rom_addr, input wire [15:0] rom_data,
    output reg tx_valid, output wire tx_ready,
    output reg [9:0] tx_addr, output reg [15:0] tx_data,
    output reg [1:0] tx_mask, output reg tx_bank,
    output wire [7:0] hpos, output wire [6:0] vpos,
    output wire hsync, output wire vsync, output wire pixel,
    output reg fence, output wire done
);
    reg [15:0] fb0 [0:767];
    reg [15:0] fb1 [0:767];
    reg [2:0] phase;
    reg [10:0] beat;
    reg [15:0] ticks;
    reg [14:0] raster;
    integer i;
    integer word_index;
    integer row_index;
    integer col_index;
    integer physical;
    integer scan_addr;
    integer sx, sy;

    // Tiles are 16x8; odd tile rows are physically wired in reverse order.
    function integer layout(input integer row, input integer col);
        integer tile_x;
        begin
            tile_x = ((row / 8) & 1) ? 11-col : col;
            layout = ((row / 8)*12 + tile_x)*8 + row%8;
        end
    endfunction

    assign rom_addr = physical;
    assign tx_ready = (ticks[1:0] != 2'b01);
    assign hpos = raster % 208;
    assign vpos = raster / 208;
    assign hsync = !(hpos >= 196 && hpos < 204);
    assign vsync = !(vpos >= 66 && vpos < 70);
    assign pixel = (hpos < 192 && vpos < 64) ? fb0[scan_addr][hpos%16] : 1'b0;
    assign done = phase == 4;

    always @* begin
        sx = hpos / 16;
        sy = vpos;
        scan_addr = (vpos < 64 && hpos < 192) ? layout(sy,sx) : 0;
        word_index = (((phase == 2) ? beat/2 : beat)*5 + 37) % 768;
        row_index = word_index / 12;
        col_index = word_index % 12;
        physical = layout(row_index,col_index);
        tx_valid = !rst && phase > 0 && phase < 4 && !fence;
        tx_bank = 1;
        tx_addr = physical;
        tx_mask = 2'b11;
        tx_data = 16'h0000;
        if (phase == 2) begin
            // Only the enabled byte is meaningful; the other byte is bus residue.
            if (!beat[0]) begin
                tx_mask = 2'b01;
                tx_data = {8'hd3,rom_data[7:0]};
            end else begin
                tx_mask = 2'b10;
                tx_data = {rom_data[15:8],8'h6b};
            end
        end
    end

    always @(posedge clk) begin
        if (rst) begin
            phase <= 1; beat <= 0; ticks <= 0; raster <= 0; fence <= 0;
            for (i=0; i<768; i=i+1) begin
                fb0[i] <= (i%8 == 0 || i%8 == 7) ? 16'hffff : 16'h8001;
                fb1[i] <= 0;
            end
        end else begin
            ticks <= ticks+1;
            raster <= (raster == 14975) ? 0 : raster+1;
            fence <= 0;
            if (tx_valid && tx_ready) begin
                if (tx_bank) begin
                    if (tx_mask[0]) fb1[tx_addr][7:0] <= tx_data[7:0];
                    if (tx_mask[1]) fb1[tx_addr][15:8] <= tx_data[15:8];
                end else begin
                    if (tx_mask[0]) fb0[tx_addr][7:0] <= tx_data[7:0];
                    if (tx_mask[1]) fb0[tx_addr][15:8] <= tx_data[15:8];
                end
                if ((phase == 2 && beat == 1535) || (phase != 2 && beat == 767)) begin
                    phase <= phase+1; beat <= 0; fence <= 1;
                end else beat <= beat+1;
            end
        end
    end
endmodule
