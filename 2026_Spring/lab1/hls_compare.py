#!/usr/bin/env python3
import argparse
import re
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

METRICS = [
    "LatencyMatch", # Latency from Synthesis
    "LatencyTime",  # Latency time (ns)
    "Interval",     # Initiation Interval
    "CosimLatency", # Latency from Co-simulation
    "LUT",
    "FF",
    "BRAM",
    "DSP"
]

def find_project_dir(log_file_path: Path) -> Optional[Path]:
    """
    Infers the project directory from the log file path.
    Assumes standard structure: .../lab1/logs/hls.log -> .../lab1/project_1
    """
    # Parent of 'logs' directory
    base_dir = log_file_path.parent.parent
    
    # Check for 'project_1'
    proj_dir = base_dir / "project_1"
    if proj_dir.exists():
        return proj_dir
    
    # Fallback: search in current dir if log is in root
    if log_file_path.parent.name != "logs":
         proj_dir = log_file_path.parent / "project_1"
         if proj_dir.exists():
             return proj_dir
             
    return None

def parse_csynth(report_path: Path) -> Dict[str, float]:
    data = {}
    if not report_path.exists():
        return data
        
    content = report_path.read_text()
    
    # NEW FORMAT (top_kernel_csynth.rpt)
    # +---------+---------+----------+----------+-------+-------+---------+
    # |  Latency (cycles) |  Latency (absolute) |    Interval   | Pipeline|
    # |   min   |   max   |    min   |    max   |  min  |  max  |   Type  |
    # +---------+---------+----------+----------+-------+-------+---------+
    # |    62213|    62213|  0.622 ms|  0.622 ms|  62214|  62214|       no|
    #
    # Regex look for the line with values.
    # We assume the line starts with "|", has digits, |, digits, ...
    
    # Try finding the "Latency (cycles)" table header first to locate the section?
    # Or just a robust regex for the value line. 
    # It has 7 columns.
    # | val | val | time | time | val | val | type |
    
    # Pattern for the value row:
    # | <digits> | <digits> | <time> | <time> | <digits> | <digits> | <text> |
    match_new = re.search(r"\|\s*(\d+)\|\s*(\d+)\|\s*[\d\.e\+\-]+\s*\w+\|\s*[\d\.e\+\-]+\s*\w+\|\s*(\d+)\|\s*(\d+)\|", content)
    if match_new:
        data["LatencyMatch"] = int(match_new.group(2)) # Max Latency
        data["Interval"] = int(match_new.group(4))     # Max Interval
        # Latency Time extraction can be tricky with units, ignoring for now or attempting simple parse
        # If needed, we can extract from group 3/4
        return data

    # OLD FORMAT (fallback)
    # |+ top_kernel | - | 0.02 | 820162 | ...
    match_old = re.search(r"\|\+\s*top_kernel\s*\|\s*-\s*\|\s*[\d\.]+\|\s*(\d+)\|\s*([\d\.e\+\-]+)\|\s*[\d\.\-]+\|\s*(\d+)\|", content)
    if match_old:
        data["LatencyMatch"] = int(match_old.group(1))
        try:
            data["LatencyTime"] = float(match_old.group(2))
        except ValueError:
            pass
        data["Interval"] = int(match_old.group(3))
        
    return data

def parse_cosim(report_path: Path) -> Dict[str, float]:
    data = {}
    if not report_path.exists():
        return data
        
    content = report_path.read_text()
    
    # |   Verilog|      Pass|         820162|         820162|         820162|...
    # Look for "Verilog" followed by "Pass"
    match = re.search(r"\|\s*Verilog\|\s*Pass\|\s*(\d+)\|", content)
    if match:
        data["CosimLatency"] = int(match.group(1))
        
    return data

def parse_impl(report_path: Path) -> Dict[str, float]:
    data = {}
    if not report_path.exists():
        return data
        
    content = report_path.read_text()
    
    # Matches both export_impl.rpt (table) and top_kernel_export.rpt (key: val)
    # LUT:\s+5243
    patterns = {
        "LUT": r"LUT:\s+(\d+)",
        "FF": r"FF:\s+(\d+)",
        "BRAM": r"BRAM:\s+(\d+)",
        "DSP": r"DSP:\s+(\d+)"
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, content)
        if match:
            data[key] = int(match.group(1))
            
    return data

def get_run_data(path_str: str) -> Dict[str, float]:
    path = Path(path_str).resolve()
    print(f"Analyzing: {path.name}")
    
    proj_dir = None
    
    # CASE 1: Path is a directory (e.g., baseline_reports)
    if path.is_dir():
        # Search for csynth report (PRIORITIZE NEW NAME)
        csynth_candidates = [
            path / "top_kernel_csynth.rpt", 
            path / "csynth.rpt", 
            path / "csynth.baseline.rpt"
        ]
        found_csynth = next((p for p in csynth_candidates if p.exists()), None)

        if found_csynth:
            proj_dir = path
            print(f"  Using provided directory as report source.")
            
            metrics = {}
            # Parse Synthesis
            print(f"  Parsing Synthesis: {found_csynth.name}")
            metrics.update(parse_csynth(found_csynth))
                
            # Parse Cosim
            cosim_candidates = [
                 path / "top_kernel_cosim.rpt", 
                 path / "top_kernel_cosim.baseline.rpt"
            ]
            found_cosim = next((p for p in cosim_candidates if p.exists()), None)
            if found_cosim:
                print(f"  Parsing Co-sim:    {found_cosim.name}")
                metrics.update(parse_cosim(found_cosim))
                
            # Parse Impl
            impl_candidates = [
                path / "top_kernel_export.rpt",
                path / "export_impl.rpt", 
                path / "export_impl.baseline.rpt"
            ]
            found_impl = next((p for p in impl_candidates if p.exists()), None)
            if found_impl:
                 print(f"  Parsing Impl:      {found_impl.name}")
                 metrics.update(parse_impl(found_impl))
            
            return metrics
            
        else:
             # Assume it's a project dir, look for standard structure
             proj_dir = path
    
    # CASE 2: Path is a log file
    elif path.is_file():
        proj_dir = find_project_dir(path)
        if not proj_dir:
            print(f"{Colors.WARNING}  Could not auto-detect 'project_1' directory for {path}{Colors.ENDC}")
            return {}
        print(f"  Found project directory: {proj_dir}")

    # Standard HLS Structure Parsing
    if not proj_dir:
        return {}
        
    metrics = {}
    
    # 1. Parse Synthesis Report (PRIORITIZE NEW NAME)
    csynth_candidates = [
        proj_dir / "hls" / "syn" / "report" / "top_kernel_csynth.rpt",
        proj_dir / "hls" / "syn" / "report" / "csynth.rpt"
    ]
    csynth_path = next((p for p in csynth_candidates if p.exists()), None)
    if csynth_path:
        print(f"  Parsing Synthesis: {csynth_path.relative_to(proj_dir)}")
        metrics.update(parse_csynth(csynth_path))

    # 2. Parse Cosim Report
    cosim_path = proj_dir / "hls" / "sim" / "report" / "top_kernel_cosim.rpt"
    if cosim_path.exists():
        print(f"  Parsing Co-sim:    {cosim_path.relative_to(proj_dir)}")
        metrics.update(parse_cosim(cosim_path))

    # 3. Parse Implementation Report (PRIORITIZE NEW NAME)
    impl_candidates = [
        proj_dir / "hls" / "impl" / "report" / "verilog" / "top_kernel_export.rpt",
        proj_dir / "hls" / "impl" / "report" / "verilog" / "export_impl.rpt"
    ]
    impl_path = next((p for p in impl_candidates if p.exists()), None)
    if impl_path:
        print(f"  Parsing Impl:      {impl_path.relative_to(proj_dir)}")
        metrics.update(parse_impl(impl_path))
        
    return metrics

def print_row(name, baseline_val, new_val, is_speedup=False, is_lower_better=True):
    if baseline_val is None and new_val is None:
        return
        
    b_str = str(baseline_val) if baseline_val is not None else "N/A"
    n_str = str(new_val) if new_val is not None else "N/A"
    
    diff_str = ""
    ratio_str = ""
    
    if baseline_val is not None and new_val is not None and baseline_val != 0 and new_val != 0:
        # Calculate ratio
        if is_speedup:
            # For speedup (latency), Higher Ratio = Better
            # Speedup = Baseline / New
            ratio = float(baseline_val) / float(new_val)
            ratio_str = f"{ratio:.2f}x"
            
            if ratio > 1.01:
                ratio_str = f"{Colors.GREEN}{ratio_str}{Colors.ENDC}"
            elif ratio < 0.99:
                ratio_str = f"{Colors.FAIL}{ratio_str}{Colors.ENDC}"
                
        else:
            # For resources, plain delta/usage
            # We don't necessarily want "speedup" for LUTs, just % change maybe?
            # Let's just show ratio as New/Baseline for resources
            ratio = float(new_val) / float(baseline_val)
            ratio_str = f"{ratio:.2f}x"
            
    print(f"| {name:<15} | {b_str:<15} | {n_str:<15} | {ratio_str:<15} |")

def main():
    parser = argparse.ArgumentParser(description="Compare HLS Run Metrics")
    parser.add_argument("baseline", help="Path to baseline log file OR directory containing report files")
    parser.add_argument("new", help="Path to new run log file OR directory")
    
    args = parser.parse_args()
    
    print(f"{Colors.HEADER}=== HLS Run Comparison ==={Colors.ENDC}\n")
    
    base_metrics = get_run_data(args.baseline)
    print("")
    new_metrics = get_run_data(args.new)
    print("")
    
    print("-" * 70)
    print(f"| {'Metric':<15} | {'Baseline':<15} | {'Current':<15} | {'Speedup':<15} |")
    print("-" * 70)
    
    # Latency (Cycles)
    print_row("Latency (Cyc)", base_metrics.get("LatencyMatch"), new_metrics.get("LatencyMatch"), is_speedup=True)
    
    # Latency (Time)
    # print_row("Latency (ns)", base_metrics.get("LatencyTime"), new_metrics.get("LatencyTime"), is_speedup=True)
    
    # Interval
    print_row("Interval", base_metrics.get("Interval"), new_metrics.get("Interval"), is_speedup=True)
    
    # Co-sim
    print_row("Co-sim (Cyc)", base_metrics.get("CosimLatency"), new_metrics.get("CosimLatency"), is_speedup=True)
    
    print("-" * 70)
    
    # Resources
    print_row("LUT", base_metrics.get("LUT"), new_metrics.get("LUT"), is_speedup=False)
    print_row("FF", base_metrics.get("FF"), new_metrics.get("FF"), is_speedup=False)
    print_row("BRAM", base_metrics.get("BRAM"), new_metrics.get("BRAM"), is_speedup=False)
    print_row("DSP", base_metrics.get("DSP"), new_metrics.get("DSP"), is_speedup=False)
    
    print("-" * 70)

if __name__ == "__main__":
    main()
