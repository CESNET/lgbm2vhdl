import os
from lgbm2vhdl.LGBM2VHDL import LGBM2VHDL

# Example model and quantization definition
model_filename = os.path.join("data", "example_model_class3.txt")
quantization_filename = os.path.join("data", "example_model_class3-quantization.csv")

# Model loading
lvg = LGBM2VHDL(model_filename, quantization_filename, working_dir="./tmp")

# Generation of VHDL files
lvg.generate_vhdl(architecture="mem-c")

# Running simulation
lvg.run_simulation(architecture="mem-c")
