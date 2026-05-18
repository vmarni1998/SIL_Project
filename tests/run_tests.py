"""
tests/run_tests.py
==================
SIL Test Orchestrator for the PID Motor Speed Controller.

What this script does:
  1. Locates the compiled shared library (libcontroller.so/.dll/.dylib)
  2. Uses Python ctypes to call the real C functions (pid_init, pid_step, pid_reset)
  3. Runs a closed-loop simulation with the Python MotorPlant for each JSON test case
  4. Evaluates PASS/FAIL against tolerance and overshoot criteria
  5. Writes a JSON report (for Jenkins to archive)
  6. Writes a JUnit-compatible XML report (for Jenkins test result graphs)
  7. Exits with code 0 if all pass, 1 if any fail (Jenkins reads this)

Usage:
  python tests/run_tests.py
  python tests/run_tests.py --output-dir tests/
  python tests/run_tests.py --lib path/to/libcontroller.so
"""

from __future__ import annotations

import argparse
import ctypes
import json
import math
import pathlib
import platform
import sys
import datetime
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# Locate plant model (one level up from tests/)
# ---------------------------------------------------------------------------
_REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT / "plant"))
from plant_model import MotorPlant   # noqa: E402  (after sys.path tweak)


# ===========================================================================
# 1. SHARED LIBRARY LOADER
# ===========================================================================

def _lib_filename() -> str:
    """Return the platform-appropriate shared library filename."""
    system = platform.system()
    if system == "Windows":
        return "controller.dll"
    if system == "Darwin":
        return "libcontroller.dylib"
    return "libcontroller.so"   # Linux / other POSIX


def find_library(override: str | None = None) -> pathlib.Path:
    """
    Search for the compiled shared library.

    Search order:
      1. --lib CLI argument (if provided)
      2. tests/  (where CMake's POST_BUILD copy puts it)
      3. build/  (CMake default output directory)
    """
    if override:
        p = pathlib.Path(override)
        if not p.exists():
            sys.exit(f"ERROR: specified library not found: {p}")
        return p

    name   = _lib_filename()
    search = [
        pathlib.Path(__file__).parent / name,           # tests/
        _REPO_ROOT / "build" / name,                    # build/
        _REPO_ROOT / "build" / "Debug"   / name,        # MSVC Debug
        _REPO_ROOT / "build" / "Release" / name,        # MSVC Release
    ]
    for candidate in search:
        if candidate.exists():
            return candidate

    sys.exit(
        f"ERROR: Could not find {name}.\n"
        f"  Run:  cmake -B build -S .  &&  cmake --build build\n"
        f"  Searched: {[str(s) for s in search]}"
    )


# ===========================================================================
# 2. CTYPES BINDING
# ===========================================================================

class PID_t(ctypes.Structure):
    """
    Must exactly mirror the PID_t struct in controller.h.
    Field order and types must match byte-for-byte.
    """
    _fields_ = [
        ("kp",          ctypes.c_float),
        ("ki",          ctypes.c_float),
        ("kd",          ctypes.c_float),
        ("integral",    ctypes.c_float),
        ("prev_error",  ctypes.c_float),
    ]


def load_controller(lib_path: pathlib.Path) -> ctypes.CDLL:
    """
    Load the shared library and declare all function signatures.
    ctypes needs explicit argtypes/restype to handle float correctly.
    """
    lib = ctypes.CDLL(str(lib_path))

    # void pid_init(PID_t*, float kp, float ki, float kd)
    lib.pid_init.restype  = None
    lib.pid_init.argtypes = [
        ctypes.POINTER(PID_t),
        ctypes.c_float, ctypes.c_float, ctypes.c_float,
    ]

    # float pid_step(PID_t*, float setpoint, float measured, float dt)
    lib.pid_step.restype  = ctypes.c_float
    lib.pid_step.argtypes = [
        ctypes.POINTER(PID_t),
        ctypes.c_float, ctypes.c_float, ctypes.c_float,
    ]

    # void pid_reset(PID_t*)
    lib.pid_reset.restype  = None
    lib.pid_reset.argtypes = [ctypes.POINTER(PID_t)]

    return lib


# ===========================================================================
# 3. CLOSED-LOOP SIMULATION
# ===========================================================================

def run_case(
    lib:       ctypes.CDLL,
    plant_cfg: dict,
    pid_cfg:   dict,
    tc:        dict,
    dt:        float,
) -> dict:
    """
    Run one test case end-to-end.

    Returns a result dict with:
      id, description, setpoint, final_speed, error,
      passed, history (list of floats), overshoot_pct
    """
    # --- Initialise controller ------------------------------------------
    pid = PID_t()
    lib.pid_init(
        ctypes.byref(pid),
        float(pid_cfg["kp"]),
        float(pid_cfg["ki"]),
        float(pid_cfg["kd"]),
    )

    # --- Initialise plant -----------------------------------------------
    plant = MotorPlant(**plant_cfg)

    # Pre-load initial speed if test case specifies a non-zero start
    initial_speed = float(tc.get("initial_speed", 0.0))
    if initial_speed != 0.0:
        # Warm up plant by driving it open-loop for a few seconds
        # so the internal state matches the desired initial speed
        warmup_steps = int(5.0 / dt)
        for _ in range(warmup_steps):
            # Drive until plant speed is close enough
            drive = 100.0 * (initial_speed / plant_cfg["max_speed"])
            plant.step(drive, dt)
        # Sync PID state to this operating point
        lib.pid_reset(ctypes.byref(pid))

    # --- Simulation loop ------------------------------------------------
    setpoint = float(tc["setpoint"])
    steps    = int(tc["duration_s"] / dt)
    history  = []          # speed samples over time
    drives   = []          # drive % over time

    current_speed = plant.true_speed

    for _ in range(steps):
        # Controller: C function, called via ctypes
        drive = lib.pid_step(
            ctypes.byref(pid),
            setpoint,
            current_speed,
            dt,
        )
        # Plant: Python function
        current_speed = plant.step(float(drive), dt)
        history.append(current_speed)
        drives.append(float(drive))

    # --- Evaluation -----------------------------------------------------
    final_speed = history[-1] if history else 0.0
    error       = abs(final_speed - setpoint)
    passed      = error <= float(tc["tolerance"])

    # Overshoot check (only for non-zero setpoints)
    overshoot_pct = 0.0
    overshoot_ok  = True
    if tc.get("check_overshoot", False) and setpoint > 0.0:
        peak          = max(history)
        overshoot_pct = ((peak - setpoint) / setpoint) * 100.0
        overshoot_ok  = overshoot_pct <= float(tc.get("max_overshoot_pct", 100.0))
        if not overshoot_ok:
            passed = False

    return {
        "id":              tc["id"],
        "requirement":     tc.get("requirement", ""),
        "description":     tc["description"],
        "setpoint":        setpoint,
        "final_speed":     round(final_speed, 4),
        "error":           round(error, 4),
        "tolerance":       float(tc["tolerance"]),
        "passed":          passed,
        "overshoot_pct":   round(overshoot_pct, 2),
        "overshoot_ok":    overshoot_ok,
        "history":         [round(s, 4) for s in history],
        "drives":          [round(d, 4) for d in drives],
    }


# ===========================================================================
# 4. REPORTING
# ===========================================================================

def print_results(suite_name: str, results: list[dict]) -> None:
    """Pretty-print results to stdout (visible in Jenkins console log)."""
    width = 60
    now   = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print()
    print("=" * width)
    print(f"  {suite_name}")
    print(f"  Run: {now}")
    print("=" * width)

    for r in results:
        status = "✓ PASS" if r["passed"] else "✗ FAIL"
        print(f"\n  [{r['id']}]  {status}  —  {r['requirement']}")
        print(f"    {r['description']}")
        print(f"    setpoint  = {r['setpoint']:.1f}")
        print(f"    final     = {r['final_speed']:.4f}")
        print(f"    error     = {r['error']:.4f}  (tol ±{r['tolerance']})")
        if r["overshoot_pct"] > 0:
            print(f"    overshoot = {r['overshoot_pct']:.2f}%")
        if not r["passed"]:
            if r["error"] > r["tolerance"]:
                print(f"    !! FAIL: error {r['error']:.4f} exceeds tolerance {r['tolerance']}")
            if not r["overshoot_ok"]:
                print(f"    !! FAIL: overshoot {r['overshoot_pct']:.2f}% exceeds limit")

    passed = sum(1 for r in results if r["passed"])
    total  = len(results)
    print()
    print("=" * width)
    print(f"  RESULT: {passed}/{total} passed", end="")
    print("  ✓ ALL PASS" if passed == total else "  ✗ FAILURES DETECTED")
    print("=" * width)
    print()


def write_json_report(results: list[dict], suite_name: str, output_dir: pathlib.Path) -> pathlib.Path:
    """Write machine-readable JSON report (for Jenkins to archive as artifact)."""
    report = {
        "suite":     suite_name,
        "timestamp": datetime.datetime.now().isoformat(),
        "passed":    sum(1 for r in results if r["passed"]),
        "total":     len(results),
        "results":   results,
    }
    path = output_dir / "sil_report.json"
    path.write_text(json.dumps(report, indent=2))
    print(f"  JSON report  → {path}")
    return path


def write_junit_xml(results: list[dict], suite_name: str, output_dir: pathlib.Path) -> pathlib.Path:
    """
    Write JUnit-compatible XML report.
    Jenkins' 'Publish JUnit test results' plugin reads this to draw
    test trend graphs and flag individual failing tests.
    """
    failures  = sum(1 for r in results if not r["passed"])
    testsuite = ET.Element("testsuite",
        name=suite_name,
        tests=str(len(results)),
        failures=str(failures),
        errors="0",
        timestamp=datetime.datetime.now().isoformat(),
    )

    for r in results:
        tc = ET.SubElement(testsuite, "testcase",
            name=f"{r['id']}: {r['description']}",
            classname="SIL.MotorController",
            time="0",
        )
        if not r["passed"]:
            msg = (
                f"final_speed={r['final_speed']}, "
                f"error={r['error']} > tolerance={r['tolerance']}"
            )
            if not r["overshoot_ok"]:
                msg += f", overshoot={r['overshoot_pct']}%"
            failure = ET.SubElement(tc, "failure", message=msg)
            failure.text = msg

    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    path = output_dir / "sil_junit.xml"
    tree.write(str(path), encoding="unicode", xml_declaration=True)
    print(f"  JUnit XML    → {path}")
    return path


# ===========================================================================
# 5. MAIN
# ===========================================================================

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="SIL Test Orchestrator")
    p.add_argument("--lib",        help="Path to libcontroller shared library")
    p.add_argument("--config",     help="Path to test_cases.json",
                   default=str(pathlib.Path(__file__).parent / "test_cases.json"))
    p.add_argument("--output-dir", help="Directory for reports",
                   default=str(pathlib.Path(__file__).parent))
    return p.parse_args()


def main() -> int:
    args       = parse_args()
    output_dir = pathlib.Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # -- Load config
    cfg_path = pathlib.Path(args.config)
    if not cfg_path.exists():
        sys.exit(f"ERROR: test config not found: {cfg_path}")
    cfg = json.loads(cfg_path.read_text())

    # -- Load C library
    lib_path = find_library(args.lib)
    print(f"\n  Loading library: {lib_path}")
    lib = load_controller(lib_path)

    # -- Run all test cases
    results = []
    for tc in cfg["test_cases"]:
        result = run_case(
            lib       = lib,
            plant_cfg = cfg["plant"],
            pid_cfg   = cfg["pid_gains"],
            tc        = tc,
            dt        = float(cfg["dt"]),
        )
        results.append(result)

    # -- Print and save
    print_results(cfg["test_suite"], results)
    write_json_report(results, cfg["test_suite"], output_dir)
    write_junit_xml(results,   cfg["test_suite"], output_dir)

    all_passed = all(r["passed"] for r in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
