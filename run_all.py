"""Run every codelab in order (use this for the 'execution' part of each video)."""
import subprocess, sys, pathlib
root = pathlib.Path(__file__).parent
for d in ["01_foundations", "02_ag_ui", "03_a2ui", "04_openui_lang", "05_json_render", "06_mcp_apps", "07_harness_genui"]:
    print(f"\n===== {d} =====", flush=True)
    subprocess.run([sys.executable, str(root / d / "demo.py")], check=True)
print("\n===== tests =====", flush=True)
subprocess.run([sys.executable, "-m", "unittest", "test_all", "-v"], cwd=root, check=True)
