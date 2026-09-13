import sys
from ams_optimizer.core.optimizer import AMSOptimizer

with open("examples/PWM_CTRL_relaxed.v", "r") as f:
    verilog = f.read()

opt = AMSOptimizer()
res = opt.run(verilog)
print(res.bom_report)
