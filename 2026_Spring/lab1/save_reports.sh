#!/bin/bash

# Default project directory (can be overridden by first argument)
PROJECT_DIR=${1:-"project_1"}

# Create a timestamped directory name
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUT_DIR="reports_${TIMESTAMP}"

# Create the directory
mkdir -p "$OUT_DIR"

echo "Collecting reports from '$PROJECT_DIR' into '$OUT_DIR'..."

# Define source files based on standard Vitis HLS structure
CSYNTH="${PROJECT_DIR}/hls/syn/report/top_kernel_csynth.rpt"
COSIM="${PROJECT_DIR}/hls/sim/report/top_kernel_cosim.rpt"
IMPL="${PROJECT_DIR}/hls/impl/report/verilog/top_kernel_export.rpt"
LOG_FILE="logs/hls_run_tcl.log"

# Counters
COUNT=0

# Copy function
copy_report() {
    src=$1
    if [ -f "$src" ]; then
        cp "$src" "$OUT_DIR/"
        echo "  [OK] Copied $(basename "$src")"
        ((COUNT++))
    else
        echo "  [WARN] Not found: $src"
    fi
}

copy_report "$CSYNTH"
copy_report "$COSIM"
copy_report "$IMPL"
copy_report "$LOG_FILE"

if [ $COUNT -eq 0 ]; then
    echo "No reports found. removing empty directory."
    rmdir "$OUT_DIR"
else
    echo "Done. Saved $COUNT reports to $OUT_DIR/"
fi
