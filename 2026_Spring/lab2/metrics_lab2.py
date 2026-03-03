
import os
import re

# File paths
CSYNTH_RPT = "project_1/hls/syn/report/top_kernel_csynth.rpt"
COSIM_RPT = "project_1/hls/sim/report/top_kernel_cosim.rpt"
EXPORT_RPT = "project_1/hls/impl/report/verilog/top_kernel_export.rpt"

# Baseline numbers (provided by user)
BASE_CYCLES = 17936266
BASE_PERIOD = 8.009
BASE_LATENCY_MS = 143.6515544

def extract_metric(file_path, pattern, group_index=1, value_type=str):
    if not os.path.exists(file_path):
        return None
    with open(file_path, "r") as f:
        content = f.read()
        match = re.search(pattern, content)
        if match:
            return value_type(match.group(group_index))
    return None

def main():
    print(f"--- Lab 2 Metrics Extraction ---")
    
    # 1. Co-Simulation Cycles (Accurate Latency)
    cosim_cycles = extract_metric(COSIM_RPT, r"Verilog\|\s*Pass\|\s*(\d+)\|", 1, int)
    if cosim_cycles:
        print(f"Co-Sim Cycles: {cosim_cycles}")
    else:
        print(f"Co-Sim Cycles: Not found (check {COSIM_RPT})")
        
    # 2. Post-Implementation Timing
    post_impl_period = extract_metric(EXPORT_RPT, r"CP achieved post-implementation:\s*([\d\.]+)", 1, float)
    if not post_impl_period:
        # Fallback to post-synthesis if implementation didn't finish/report
        post_impl_period = extract_metric(EXPORT_RPT, r"CP achieved post-synthesis:\s*([\d\.]+)", 1, float)
        if post_impl_period:
             print(f"Clock Period: {post_impl_period} ns (Post-Synthesis)")
        else:
             print(f"Clock Period: Not found in {EXPORT_RPT}")
    else:
        print(f"Clock Period: {post_impl_period} ns (Post-Implementation)")

    # 3. Resources
    luts = extract_metric(EXPORT_RPT, r"LUT:\s*(\d+)", 1, int)
    ffs = extract_metric(EXPORT_RPT, r"FF:\s*(\d+)", 1, int)
    brams = extract_metric(EXPORT_RPT, r"BRAM:\s*(\d+)", 1, int)
    dsps = extract_metric(EXPORT_RPT, r"DSP:\s*(\d+)", 1, int)
    
    print(f"Resources: LUT={luts}, FF={ffs}, BRAM={brams}, DSP={dsps}")
    
    # 4. Speedup Calculation
    if cosim_cycles and post_impl_period:
        opt_latency_ns = cosim_cycles * post_impl_period
        opt_latency_ms = opt_latency_ns / 1e6
        speedup = BASE_LATENCY_MS / opt_latency_ms
        
        print(f"\n--- Final Results ---")
        print(f"Baseline Latency: {BASE_LATENCY_MS:.4f} ms")
        print(f"Optimized Latency: {opt_latency_ms:.4f} ms")
        print(f"Speedup: {speedup:.2f}x")
        
        print(f"\n--- Markdown Table ---")
        print(f"| Metric | Baseline | Optimized | Speedup |")
        print(f"| :--- | :--- | :--- | :--- |")
        print(f"| Cycle Count | {BASE_CYCLES} | {cosim_cycles} | {BASE_CYCLES/cosim_cycles:.2f}x |")
        print(f"| Clock Period | {BASE_PERIOD} ns | {post_impl_period} ns | {BASE_PERIOD/post_impl_period:.2f}x |")
        print(f"| Total Latency | {BASE_LATENCY_MS:.4f} ms | {opt_latency_ms:.4f} ms | **{speedup:.2f}x** |")

if __name__ == "__main__":
    main()
