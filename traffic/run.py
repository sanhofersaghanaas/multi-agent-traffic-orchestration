"""
Entry point for P25 Multi-Modal Traffic Orchestration Network.
Usage:
    python run.py --dashboard   # Launches Streamlit web dashboard
    python run.py --benchmark   # Runs multi-seed comparative benchmark suite
    python run.py --scenario    # Regenerates SUMO network and route files
"""

import os
import sys
import argparse
import subprocess

def setup_environment():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)
    return base_dir

def main():
    base_dir = setup_environment()
    parser = argparse.ArgumentParser(description="P25 Dynamic Multi-Modal Traffic Orchestration Network")
    parser.add_argument("--dashboard", action="store_true", help="Launch Streamlit interactive dashboard")
    parser.add_argument("--benchmark", action="store_true", help="Run multi-seed comparative evaluation")
    parser.add_argument("--scenario", action="store_true", help="Generate SUMO network and route scenarios")
    parser.add_argument("--port", type=int, default=8501, help="Port for Streamlit dashboard")
    
    args = parser.parse_args()
    
    # 1. Generate scenario files if missing
    from sumo_files.generate_scenario import generate_network_xml, generate_routes_xml
    net_file = os.path.join(base_dir, "sumo_files", "network.nod.xml")
    if not os.path.exists(net_file) or args.scenario:
        print("[*] Generating SUMO network and multi-modal route scenario files...")
        generate_network_xml(os.path.join(base_dir, "sumo_files"))
        generate_routes_xml(os.path.join(base_dir, "sumo_files"), seed=42)
        print("[+] Scenario generated successfully.")
        
    # 2. Run Benchmark if requested
    if args.benchmark:
        from experiments.benchmark_runner import run_full_benchmark
        print("[*] Executing multi-seed benchmark runner...")
        run_full_benchmark()
        return

    # 3. Default to launching dashboard
    app_path = os.path.join(base_dir, "dashboard", "app.py")
    print(f"[*] Starting P25 Streamlit Dashboard on port {args.port}...")
    cmd = [sys.executable, "-m", "streamlit", "run", app_path, "--server.port", str(args.port), "--server.headless", "false"]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n[+] Dashboard stopped.")

if __name__ == "__main__":
    main()
