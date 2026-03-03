#!/usr/bin/env python3
import argparse
import shutil
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Collect Vitis HLS reports and copy them to a baseline directory with a prefix.")
    parser.add_argument("prefix", help="Prefix to prepend to the report filenames (e.g., 'baseline').")
    parser.add_argument("--out-dir", default="baseline_reports", help="Output directory to store reports (default: baseline_reports).")
    parser.add_argument("--project-dir", default="project_1", help="Path to the HLS project directory (default: project_1).")
    
    args = parser.parse_args()
    
    prefix = args.prefix
    out_dir = Path(args.out_dir)
    proj_dir = Path(args.project_dir)
    
    if not proj_dir.exists():
        print(f"Error: Project directory '{proj_dir}' does not exist.")
        sys.exit(1)

    # Ensure output directory exists
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Define source paths relative to project directory and their target suffixes
    # Target name will be: {prefix}{suffix}
    # Note: Using consistent suffixes that help identify the file type
    files_to_collect = [
        # Source Path inside project_dir                                      Target Suffix
        ("hls/syn/report/csynth.rpt",                                         "_csynth.rpt"),
        ("hls/sim/report/top_kernel_cosim.rpt",                               "_cosim.rpt"),
        ("hls/impl/report/verilog/export_impl.rpt",                            "_export.rpt"),
        # Fallback/Alternative paths if flow varies slightly
        ("solution1/syn/report/csynth.rpt",                                   "_csynth.rpt"),
        ("solution1/sim/report/top_kernel_cosim.rpt",                         "_cosim.rpt"),
        ("solution1/impl/report/verilog/export_impl.rpt",                      "_export.rpt"),
    ]
    
    collected_count = 0
    
    print(f"Collecting reports from '{proj_dir}' to '{out_dir}' with prefix '{prefix}'...")
    
    # Track which suffixes we've already handled to avoid duplicates from fallback paths
    handled_suffixes = set()

    for rel_path, suffix in files_to_collect:
        if suffix in handled_suffixes:
            continue
            
        src_path = proj_dir / rel_path
        if src_path.exists():
            dest_name = f"{prefix}{suffix}"
            dest_path = out_dir / dest_name
            
            try:
                shutil.copy2(src_path, dest_path)
                print(f"  [OK] Copied {src_path} -> {dest_path}")
                collected_count += 1
                handled_suffixes.add(suffix)
            except Exception as e:
                print(f"  [Error] Failed to copy {src_path}: {e}")
        else:
            # Don't print error for fallback paths unless we really missed the main ones
            # For now, just silent skip, we'll check handled_suffixes later
            pass

    # Check if we missed any key files based on suffixes
    # We expect at least csynth
    if "_csynth.rpt" not in handled_suffixes:
         print(f"  [Warning] Could not find synthesis report (csynth.rpt) in {proj_dir}")

    print(f"\nDone. Collected {collected_count} files.")

if __name__ == "__main__":
    main()
