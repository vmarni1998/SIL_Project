"""
plant/plant_model.py
====================
Virtual DC motor plant model for SIL simulation.

Replaces real hardware by computing: given a drive signal (0-100 %),
what speed would a real motor produce after dt seconds?

Physics used:
  - First-order lag (RC-like) to model mechanical inertia
  - Coulomb + viscous friction opposing motion
  - Hard speed limit (motor back-EMF saturation)

Usage (standalone self-test):
  python plant/plant_model.py
"""

from __future__ import annotations
import math


class MotorPlant:
    """
    Simulates a DC motor as a first-order dynamical system.

    Parameters
    ----------
    max_speed     : float
        Maximum achievable speed at 100 % drive (arbitrary units,
        e.g. RPM or m/s — must match controller setpoint units).
    time_constant : float
        τ (tau) — mechanical time constant in seconds.
        Smaller = faster motor response.
    friction      : float
        Viscous friction coefficient (speed loss per second per unit speed).
        Models bearing drag, air resistance, etc.
    noise_std     : float
        Standard deviation of Gaussian sensor noise added to the
        returned speed reading. 0.0 = ideal (noiseless) sensor.
    """

    def __init__(
        self,
        max_speed: float     = 100.0,
        time_constant: float = 0.5,
        friction: float      = 0.02,
        noise_std: float     = 0.0,
    ) -> None:
        self.max_speed     = float(max_speed)
        self.tau           = float(time_constant)
        self.friction      = float(friction)
        self.noise_std     = float(noise_std)

        # Internal state — true physical speed (not measured)
        self._true_speed: float = 0.0

    # ── Public interface ──────────────────────────────────────────────────

    def step(self, drive_pct: float, dt: float) -> float:
        """
        Advance the plant simulation by one time step.

        Parameters
        ----------
        drive_pct : float
            Controller output in [0.0, 100.0].
        dt        : float
            Time step duration in seconds (must match controller dt).

        Returns
        -------
        float
            Measured speed (true speed + optional sensor noise).
        """
        if dt <= 0.0:
            raise ValueError(f"dt must be > 0, got {dt}")

        drive_pct = max(0.0, min(drive_pct, 100.0))   # safety clamp

        # Target speed the motor approaches under this drive level
        target_speed = (drive_pct / 100.0) * self.max_speed

        # First-order lag: exponential approach to target
        #   Continuous: dv/dt = (target - v) / τ
        #   Discretised (exact ZOH): v[k+1] = target + (v[k]-target)*e^(-dt/τ)
        alpha            = math.exp(-dt / self.tau)
        self._true_speed = target_speed + (self._true_speed - target_speed) * alpha

        # Apply viscous friction loss
        self._true_speed *= (1.0 - self.friction * dt)

        # Hard physical limits
        self._true_speed = max(0.0, min(self._true_speed, self.max_speed))

        # Return noisy measurement (or exact if noise_std == 0)
        return self._measured_speed()

    def reset(self) -> None:
        """
        Reset plant to standstill.
        Call between test cases so each starts from the same initial state.
        """
        self._true_speed = 0.0

    @property
    def true_speed(self) -> float:
        """True internal speed (without sensor noise)."""
        return self._true_speed

    # ── Private helpers ───────────────────────────────────────────────────

    def _measured_speed(self) -> float:
        """Add Gaussian sensor noise if configured."""
        if self.noise_std == 0.0:
            return self._true_speed
        import random
        noisy = self._true_speed + random.gauss(0.0, self.noise_std)
        return max(0.0, noisy)

    def __repr__(self) -> str:
        return (
            f"MotorPlant(max_speed={self.max_speed}, "
            f"tau={self.tau}, friction={self.friction}, "
            f"speed={self._true_speed:.3f})"
        )


# ── Standalone self-test ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  Motor Plant Self-Test")
    print("  Applying 80% drive for 3 seconds (dt=0.1s)")
    print("=" * 55)

    plant = MotorPlant(max_speed=100.0, time_constant=0.5, friction=0.02)
    t = 0.0
    dt = 0.1

    for _ in range(30):
        speed = plant.step(80.0, dt)
        bar   = "█" * int(speed / 2)
        print(f"  t={t:4.1f}s  speed={speed:6.2f}  {bar}")
        t += dt

    print()
    print("  Applying 0% drive (braking) for 2 seconds")
    for _ in range(20):
        speed = plant.step(0.0, dt)
        bar   = "█" * int(speed / 2)
        print(f"  t={t:4.1f}s  speed={speed:6.2f}  {bar}")
        t += dt

    print("=" * 55)
    print("  Self-test complete — no crashes = plant model OK")
    print("=" * 55)
