/*
 * controller.h
 * Public interface for the PID motor speed controller.
 * This header is shared between the C implementation and
 * the Python ctypes layer in the SIL test harness.
 */

#ifndef CONTROLLER_H
#define CONTROLLER_H

#ifdef __cplusplus
extern "C" {
#endif

/* ── PID state structure ─────────────────────────────────────────────────
 * All fields are float to match typical embedded MCU usage.
 * The Python ctypes struct MUST mirror this layout exactly.
 */
typedef struct {
    float kp;           /* Proportional gain                  */
    float ki;           /* Integral gain                      */
    float kd;           /* Derivative gain                    */
    float integral;     /* Accumulated integral term          */
    float prev_error;   /* Error from previous step           */
} PID_t;

/* ── API ─────────────────────────────────────────────────────────────── */

/**
 * pid_init  — Initialise (or re-initialise) a PID controller.
 * @pid : pointer to an uninitialised PID_t
 * @kp  : proportional gain
 * @ki  : integral gain
 * @kd  : derivative gain
 */
void  pid_init(PID_t *pid, float kp, float ki, float kd);

/**
 * pid_step  — Compute one control output sample.
 * @pid      : pointer to an initialised PID_t
 * @setpoint : desired output value
 * @measured : current measured value (from plant / sensor)
 * @dt       : elapsed time since last call (seconds)
 * Returns   : clamped drive signal in [0.0, 100.0]
 */
float pid_step(PID_t *pid, float setpoint, float measured, float dt);

/**
 * pid_reset — Zero the integrator and previous-error fields.
 * Call between test cases to start from a clean state.
 */
void  pid_reset(PID_t *pid);

#ifdef __cplusplus
}
#endif

#endif /* CONTROLLER_H */
