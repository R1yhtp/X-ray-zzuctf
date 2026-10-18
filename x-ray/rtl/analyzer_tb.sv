`timescale 1ns/1ps
// The acquisition engine latches DUT signals BEFORE each rising clock edge.
// VCD sample=1 marks a complete record, not a DUT clock edge.
module analyzer_tb;
    reg clk=0, rst=1;
    wire [9:0] rom_addr;
    reg [15:0] rom[0:767];
    wire [15:0] rom_data = rom[rom_addr];
    wire tx_valid,tx_ready,tx_bank,hsync,vsync,pixel,fence,done;
    wire [9:0] tx_addr;
    wire [15:0] tx_data;
    wire [1:0] tx_mask;
    wire [7:0] hpos;
    wire [6:0] vpos;
    display_core dut(.*);
    always #5 clk=~clk;

    integer fd, ignored, probes, trigger_mode, skip, take;
    integer cycle, events, captured;
    reg [2047:0] romfile, outfile;

    task declare_signals;
        begin
            $fdisplay(fd,"$version X-ray acquisition engine v1 $end");
            $fdisplay(fd,"$timescale 1ns $end");
            $fdisplay(fd,"$scope module analyzer $end");
            $fdisplay(fd,"$var wire 1 ! sample $end");
            if (probes & 1) $fdisplay(fd,"$var wire 1 A tx_valid $end");
            if (probes & 2) $fdisplay(fd,"$var wire 1 B tx_ready $end");
            if (probes & 4) $fdisplay(fd,"$var wire 1 C tx_bank $end");
            if (probes & 8) $fdisplay(fd,"$var wire 2 D tx_mask $end");
            if (probes & 16) $fdisplay(fd,"$var wire 10 E tx_addr $end");
            if (probes & 32) $fdisplay(fd,"$var wire 16 F tx_data $end");
            if (probes & 64) $fdisplay(fd,"$var wire 1 G hsync $end");
            if (probes & 128) $fdisplay(fd,"$var wire 1 H vsync $end");
            if (probes & 256) $fdisplay(fd,"$var wire 1 I pixel $end");
            if (probes & 512) $fdisplay(fd,"$var wire 1 J fence $end");
            if (probes & 1024) $fdisplay(fd,"$var wire 8 K hpos $end");
            if (probes & 2048) $fdisplay(fd,"$var wire 7 L vpos $end");
            $fdisplay(fd,"$upscope $end\n$enddefinitions $end\n#0\n0!");
        end
    endtask

    task capture;
        begin
            $fdisplay(fd,"#%0d",$time);
            if (probes & 1) $fdisplay(fd,"b%b A",tx_valid);
            if (probes & 2) $fdisplay(fd,"b%b B",tx_ready);
            if (probes & 4) $fdisplay(fd,"b%b C",tx_bank);
            if (probes & 8) $fdisplay(fd,"b%b D",tx_mask);
            if (probes & 16) $fdisplay(fd,"b%b E",tx_addr);
            if (probes & 32) $fdisplay(fd,"b%b F",tx_data);
            if (probes & 64) $fdisplay(fd,"b%b G",hsync);
            if (probes & 128) $fdisplay(fd,"b%b H",vsync);
            if (probes & 256) $fdisplay(fd,"b%b I",pixel);
            if (probes & 512) $fdisplay(fd,"b%b J",fence);
            if (probes & 1024) $fdisplay(fd,"b%b K",hpos);
            if (probes & 2048) $fdisplay(fd,"b%b L",vpos);
            $fdisplay(fd,"1!\n#%0d\n0!",$time+1);
            captured=captured+1;
        end
    endtask

    initial begin
        ignored=$value$plusargs("rom=%s",romfile);
        ignored=$value$plusargs("out=%s",outfile);
        ignored=$value$plusargs("probes=%d",probes);
        ignored=$value$plusargs("trigger=%d",trigger_mode);
        ignored=$value$plusargs("skip=%d",skip);
        ignored=$value$plusargs("take=%d",take);
        $readmemh(romfile,rom);
        fd=$fopen(outfile,"w");
        declare_signals(); events=0;captured=0;
        repeat(3) @(negedge clk);
        rst=0; #1;
        for(cycle=0;cycle<32768;cycle=cycle+1) begin
            // Sample at the falling edge, one half cycle before the transaction.
            if(trigger_mode == 0 || (trigger_mode == 1 && tx_valid) || (trigger_mode == 2 && !vsync)) begin
                if(events>=skip && captured<take) capture();
                events=events+1;
            end
            @(negedge clk);
        end
        $fclose(fd);
        $display("ACQ %0d %0d",captured,events);
        $finish;
    end
endmodule
