"""Unit tests for Formal FSM State-Space, Deadlock, and Self-Recovery Verifier."""

import unittest
import os
from espresso_mv_optimizer.extractor import UnifiedRTLExtractor
from espresso_mv_optimizer.state_verifier import StateSpaceVerifier


class TestStateSpaceVerifier(unittest.TestCase):
    """Test suite for exhaustive formal state-space verification."""

    def test_pwm_ctrl_state_space_and_deadlocks(self):
        """Verifies that PWM_CTRL has 0 deadlocks and self-recovers in <= 16 cycles."""
        verilog_path = "examples/PWM_CTRL.v"
        self.assertTrue(os.path.exists(verilog_path), f"Missing {verilog_path}")

        extractor = UnifiedRTLExtractor(verilog_path)
        self.assertEqual(extractor.total_ffs, 7)

        tts = extractor.extract_truth_tables("exact")
        verifier = StateSpaceVerifier(extractor)
        audit = verifier.verify(tts)

        self.assertTrue(audit["is_sequential"])
        self.assertEqual(audit["total_ffs"], 7)
        self.assertEqual(audit["total_states"], 128)
        self.assertEqual(audit["deadlocks_count"], 0)
        self.assertEqual(len(audit["deadlocks"]), 0)
        self.assertTrue(audit["passed"])
        self.assertLessEqual(audit["max_recovery_depth"], 16)
        self.assertIn(16, audit["cycle_lengths"])

    def test_synthetic_deadlock_detection(self):
        """Verifies that an intentional FSM deadlock is caught by the verifier."""
        synthetic_v = """
        module faulty_fsm (
            input wire clk,
            input wire rst_n,
            input wire mode,
            output reg [1:0] state
        );
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    state <= 2'b00;
                end else begin
                    if (state == 2'b11) begin
                        state <= 2'b11; // Intentional deadlock!
                    end else begin
                        state <= state + 1'b1;
                    end
                end
            end
        endmodule
        """
        extractor = UnifiedRTLExtractor(synthetic_v)
        tts = extractor.extract_truth_tables("exact")
        verifier = StateSpaceVerifier(extractor)
        audit = verifier.verify(tts)

        self.assertTrue(audit["is_sequential"])
        self.assertEqual(audit["total_ffs"], 2)
        self.assertEqual(audit["total_states"], 4)
        # In both modes (mode=0, mode=1), state 3 (2'b11) deadlocks:
        self.assertFalse(audit["passed"])
        self.assertGreater(audit["deadlocks_count"], 0)
        stuck_states = [st for (_, st) in audit["deadlocks"]]
        self.assertIn(3, stuck_states)

    def test_pure_combinational_circuit(self):
        """Verifies that pure combinational circuits (0 FFs) pass gracefully."""
        comb_v = """
        module comb_alu (
            input wire [1:0] a,
            input wire [1:0] b,
            output wire [2:0] sum
        );
            assign sum = a + b;
        endmodule
        """
        extractor = UnifiedRTLExtractor(comb_v)
        tts = extractor.extract_truth_tables("exact")
        verifier = StateSpaceVerifier(extractor)
        audit = verifier.verify(tts)

        self.assertFalse(audit["is_sequential"])
        self.assertEqual(audit["total_ffs"], 0)
        self.assertEqual(audit["deadlocks_count"], 0)
        self.assertTrue(audit["passed"])


if __name__ == "__main__":
    unittest.main()
