/*
 * main_stub.c
 * Minimal entry point used to verify the build is healthy.
 * This is NOT the test harness — the real testing is done
 * by Python in tests/run_tests.py via ctypes.
 *
 * Run after cmake --build build:
 *   ./build/sil_main
 * Expected output:
 *   [STUB] pid_step output: 100.00%
 *   [STUB] After reset, integral should be 0 — OK
 */

#include <stdio.h>
#include "controller.h"

int main(void)
{
    PID_t pid;

    /* Initialise with typical gains */
    pid_init(&pid, 1.2f, 0.4f, 0.05f);

    /* First step: setpoint=100, measured=0, dt=10ms */
    float out = pid_step(&pid, 100.0f, 0.0f, 0.01f);
    printf("[STUB] pid_step output: %.2f%%\n", out);

    /* Reset and verify integrator is cleared */
    pid_reset(&pid);
    if (pid.integral == 0.0f && pid.prev_error == 0.0f)
        printf("[STUB] After reset, integral should be 0 — OK\n");
    else
        printf("[STUB] ERROR: reset did not zero state!\n");

    return 0;
}
