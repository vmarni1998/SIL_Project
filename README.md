# SIL Motor Speed Controller

Software-in-the-Loop (SIL) testing infrastructure for a PID motor speed controller.  
Real C production code, Python plant model, automated test orchestration, Jenkins CI.

---

## Project structure

```
sil_project/
├── src/
│   ├── controller.h        # Public API (PID_t struct + function declarations)
│   ├── controller.c        # PID implementation (the code under test)
│   └── main_stub.c         # Minimal C entry point for build verification
├── plant/
│   └── plant_model.py      # Python DC motor simulation (virtual hardware)
├── tests/
│   ├── test_cases.json     # All test cases — edit here to add/change tests
│   └── run_tests.py        # Test orchestrator (loads C lib via ctypes)
├── CMakeLists.txt          # Build system — compiles C into shared library
├── Jenkinsfile             # CI/CD pipeline — triggered on every PR
└── .gitignore
```

---

## Quick start

### Prerequisites

| Tool    | Minimum version |
|---------|----------------|
| cmake   | 3.16           |
| gcc / clang | C11 support |
| python3 | 3.8            |
| git     | any            |

### 1 — Clone and build

```bash
git clone https://github.com/<your-org>/sil_project.git
cd sil_project

# Configure (creates build/ directory)
cmake -B build -S .

# Compile shared library + stub executable
cmake --build build

# Verify the build
./build/sil_main
# Expected:
#   [STUB] pid_step output: 100.00%
#   [STUB] After reset, integral should be 0 — OK
```

### 2 — Run the plant self-test

```bash
python3 plant/plant_model.py
```

You will see the simulated motor speed rising from 0 toward 80 (80 % drive applied),  
then falling back to 0 when drive is removed. This confirms the plant model is working.

### 3 — Run the full SIL test suite

```bash
python3 tests/run_tests.py
```

Expected output (all 6 test cases):

```
============================================================
  Motor Speed Controller — SIL v1.0
  Run: 2025-09-14 10:32:07
============================================================

  [TC_001]  ✓ PASS  —  REQ-CTRL-001
    Step from 0 to 50% speed — mid-range setpoint tracking
    setpoint  = 50.0
    final     = 49.8120
    error     = 0.1880  (tol ±2.0)

  ... (all 6 pass) ...

============================================================
  RESULT: 6/6 passed  ✓ ALL PASS
============================================================

  JSON report  → tests/sil_report.json
  JUnit XML    → tests/sil_junit.xml
```

---

## Adding a new test case

Open `tests/test_cases.json` and append to the `test_cases` array:

```json
{
  "id": "TC_007",
  "requirement": "REQ-CTRL-007",
  "description": "Your description here",
  "setpoint": 60.0,
  "initial_speed": 0.0,
  "duration_s": 3.0,
  "tolerance": 2.0,
  "check_overshoot": true,
  "max_overshoot_pct": 10.0
}
```

No Python or C changes needed — commit and push; Jenkins will pick it up.

---

## Jenkins CI setup

See `jenkins/JENKINS_SETUP.md` for step-by-step instructions to configure  
Jenkins to run this pipeline automatically on every Pull Request.

### What Jenkins does on each PR

```
Checkout  →  Verify Tools  →  CMake Configure  →  Build Library
     →  Plant Self-Test  →  SIL Tests  →  Archive Reports
```

- **Green PR** → all 6 test cases pass, Jenkins marks the build SUCCESS.
- **Red PR**   → any test fails, Jenkins marks FAILED and blocks the merge (if branch protection is enabled).
- **Reports**  → `sil_report.json` and `sil_junit.xml` are archived as Jenkins artifacts.
- **Graphs**   → JUnit trend graph shows pass/fail history across all builds.

---

## How SIL works — architecture

```
┌─────────────────────────────────────────────────────────┐
│  Python test orchestrator  (tests/run_tests.py)          │
│                                                          │
│   ┌──────────────┐    drive%    ┌──────────────────┐    │
│   │  C controller│ ──────────▶  │  Python plant    │    │
│   │  (ctypes)    │              │  (MotorPlant)    │    │
│   │  pid_step()  │ ◀──────────  │  step()          │    │
│   └──────────────┘   speed      └──────────────────┘    │
│                                                          │
│   JSON test cases → setpoint, duration, tolerance        │
│   Reports → sil_report.json, sil_junit.xml               │
└─────────────────────────────────────────────────────────┘
```

The C code is compiled once into a shared library.  
Python loads it at runtime — no hardware needed, no flashing, no JTAG.

---

## License

MIT — see LICENSE file.
