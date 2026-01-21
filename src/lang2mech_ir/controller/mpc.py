"""Simplified MPC controller inspired by Section 5 of the research plan."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import scipy.sparse as sp
import osqp

from ..ir_schema import MechanicsIR
from .state import ControllerConfig, PegInHoleState, MPCPlan


@dataclass
class PegInHoleMPC:
    """Quadratic-programming-based MPC that enforces IR-derived limits."""

    config: ControllerConfig = field(default_factory=ControllerConfig)

    def plan(self, ir: MechanicsIR, state: PegInHoleState) -> MPCPlan:
        horizon = self.config.horizon
        dt = self.config.timestep_s
        mass = self.config.mass_kg
        k_spring = self.config.spring_k

        depth_goal = float(ir.hole.depth_m)
        max_force = float(ir.max_force.maximum or 10.0)
        vel_limit = min(
            abs(ir.trajectory.insertion_speed_mps) * 1.2,
            self.config.velocity_limit_mps,
        )
        acc_limit = self.config.acceleration_limit_mps2

        # Linear dynamics matrices for a double integrator.
        A = np.array([[1.0, dt], [0.0, 1.0]], dtype=float)
        B = np.array([[0.5 * dt * dt], [dt]], dtype=float)

        A_powers = [np.eye(2)]
        for _ in range(1, horizon + 1):
            A_powers.append(A_powers[-1] @ A)

        base_pos = np.zeros(horizon)
        base_vel = np.zeros(horizon)
        pos_coeff = np.zeros((horizon, horizon))
        vel_coeff = np.zeros((horizon, horizon))

        s0 = np.array([state.position_m, state.velocity_mps])
        for k in range(horizon):
            base_state = A_powers[k + 1] @ s0
            base_pos[k] = base_state[0]
            base_vel[k] = base_state[1]
            for j in range(k + 1):
                contrib = A_powers[k - j] @ B
                pos_coeff[k, j] = contrib[0, 0]
                vel_coeff[k, j] = contrib[1, 0]

        c_pos = base_pos - depth_goal
        c_vel = base_vel

        H = horizon
        z_dim = 2 * H
        P = np.zeros((z_dim, z_dim))
        q = np.zeros(z_dim)

        position_weight = self.config.position_weight
        velocity_weight = self.config.velocity_weight
        control_weight = self.config.control_weight
        slack_weight = self.config.force_slack_weight

        P[:H, :H] += 2.0 * (
            position_weight * pos_coeff.T @ pos_coeff
            + velocity_weight * vel_coeff.T @ vel_coeff
            + control_weight * np.eye(H)
        )
        q[:H] += 2.0 * (
            position_weight * pos_coeff.T @ c_pos
            + velocity_weight * vel_coeff.T @ c_vel
        )

        # Slack penalty (diagonal block for slack variables)
        slack_diag = 2.0 * slack_weight * np.eye(H)
        P[H:, H:] = slack_diag

        constraints_matrix_rows = []
        lower_bounds = []
        upper_bounds = []

        def add_constraint(row, lower, upper):
            constraints_matrix_rows.append(row)
            lower_bounds.append(lower)
            upper_bounds.append(upper)

        # Force constraints: mass * a +/- slack <= max_force
        for k in range(H):
            row = np.zeros(z_dim)
            row[k] = mass
            row[H + k] = -1.0
            add_constraint(row, -np.inf, max_force)

            row = np.zeros(z_dim)
            row[k] = -mass
            row[H + k] = -1.0
            add_constraint(row, -np.inf, max_force)

        # Slack >= 0
        for k in range(H):
            row = np.zeros(z_dim)
            row[H + k] = 1.0
            add_constraint(row, 0.0, np.inf)

        # Velocity limits on predicted states
        for k in range(H):
            row = np.zeros(z_dim)
            row[:H] = vel_coeff[k]
            add_constraint(row, -vel_limit - base_vel[k], vel_limit - base_vel[k])

        # Acceleration limits
        for k in range(H):
            row = np.zeros(z_dim)
            row[k] = 1.0
            add_constraint(row, -acc_limit, acc_limit)

        # Assemble sparse matrices for OSQP
        A_con = sp.csc_matrix(np.vstack(constraints_matrix_rows))
        P_mat = sp.csc_matrix(P)
        q_vec = q
        l_vec = np.array(lower_bounds)
        u_vec = np.array(upper_bounds)

        solver = osqp.OSQP()
        solver.setup(P=P_mat, q=q_vec, A=A_con, l=l_vec, u=u_vec, verbose=False, warm_starting=True)
        result = solver.solve()

        status = getattr(result.info, "status", "")
        if status not in {"solved", "solved inaccurate"}:
            return MPCPlan(control_sequence=[0.0], predicted_positions=[state.position_m], predicted_velocities=[state.velocity_mps], cost=None)

        z_sol = result.x
        controls = z_sol[:H]
        plan = MPCPlan(control_sequence=controls.tolist(), cost=result.info.obj_val)

        pred_positions = []
        pred_velocities = []
        for k in range(H):
            pos = base_pos[k] + pos_coeff[k] @ controls
            vel = base_vel[k] + vel_coeff[k] @ controls
            # Soft contact penalty to mimic MuJoCo's spring when past goal depth
            if pos >= depth_goal:
                penetration = pos - depth_goal
                force = k_spring * penetration
                if force > max_force:
                    pos = depth_goal + max_force / k_spring
            pred_positions.append(pos)
            pred_velocities.append(vel)
        plan.predicted_positions = pred_positions
        plan.predicted_velocities = pred_velocities
        return plan

    def compute_control(self, ir: MechanicsIR, state: PegInHoleState) -> float:
        plan = self.plan(ir, state)
        return plan.first_control()
