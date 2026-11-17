import sys, runpy, traceback
P = "/home/rhy/strata-fleet/repos/OpenAirShips/CurrentModel/Analysis/check_outputs.py"
sys.argv = [P] + [a for a in sys.argv[1:] if "run_checked" not in a]
try:
    runpy.run_path(P, run_name="__main__")
except SystemExit as e:
    print("SystemExit", e.code)
except Exception:
    print("TRACEBACK:")
    traceback.print_exc()
