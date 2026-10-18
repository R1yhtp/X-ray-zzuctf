#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p build
"${IVERILOG:-iverilog}" -g2012 -s analyzer_tb -o build/sim.vvp rtl/display_core.sv rtl/analyzer_tb.sv
echo 'Built build/sim.vvp. Run: GZCTF_FLAG=zzuctf{local_test} python3 app/server.py'
