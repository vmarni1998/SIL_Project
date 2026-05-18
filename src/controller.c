/*
 * controller.c
 * PID motor speed controller implementation.
 *
 * Compiled by CMake into a shared library (libcontroller.so / .dll / .dylib)
 * so that Python can load it via ctypes during SIL simulation.
 */

#include "controller.h"
#include <stddef.h>   /* NULL */

/* ── Internal helpers ────────────────────────────────────────────────── */

/**
 * clamp  — Restrict a float value to [lo, hi].
 * Used to model actuator saturation (motor drive 0–100 %).
 */
static float clamp(float v, float lo, float hi)
{
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

/* ── Public API ──────────────────────────────────────────────────────── */

void pid_init(PID_t *pid, float kp, float ki, float kd)
{
    if (pid == NULL) return;
    pid->kp         = kp;
    pid->ki         = ki;
    pid->kd         = kd;
    pid->integral   = 0.0f;
    pid->prev_error = 0.0f;
}

float pid_step(PID_t *pid, float setpoint, float measured, float dt)
{
    if (pid == NULL || dt <= 0.0f) return 0.0f;

    /* Error between desired and actual */
    float error = setpoint - measured;

    /* Integrate error over time (trapezoidal approximation) */
    pid->integral += error * dt;

    /* Rate of change of error */
    float derivative = (error - pid->prev_error) / dt;

    /* Store error for next iteration */
    pid->prev_error = error;

    /* PID output */
    float output = (pid->kp * error)
                 + (pid->ki * pid->integral)
                 + (pid->kd * derivative);

    /* Clamp to valid actuator range: 0 – 100 % drive */
    return clamp(output, 0.0f, 100.0f);
}

void pid_reset(PID_t *pid)
{
    if (pid == NULL) return;
    pid->integral   = 0.0f;
    pid->prev_error = 0.0f;
}
