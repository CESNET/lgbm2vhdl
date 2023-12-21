import os
from .GenVHDLCommon import GenVHDLCommon
from .GenVHDLMemC import GenVHDLMemC
from .GenVHDLMemC_Ord import GenVHDLMemC_Ord
from .GenVHDLMemC_Mem import GenVHDLMemC_Mem
from .GenVHDLMemC_Ord_Mem import GenVHDLMemC_Ord_Mem
from .GenVHDLWrapper import GenVHDLWrapper
from .GenVHDLTestbench import GenVHDLTestbench
from .LGBModel import LGBModel
from .RunSimulation import RunSimulation
from .Common import generate_build_files

class LGBM2VHDL:
    
    def __init__(self, model_filename, quantization_filename, working_dir):
        self.working_dir = os.path.abspath(working_dir) 
        print("LightGBM Model Loading...")
        self.lgb_model = LGBModel(model_filename, quantization_filename)
        print("Done")

    def generate_vhdl(self, architecture, iters=None):
        if iters is None:
            iters = self.lgb_model.num_iterations
        print("VHDL Generation...")
        output_dir = os.path.join(self.working_dir, architecture)

        if architecture == "mem-c":
            gen_mem_c = GenVHDLMemC(self.lgb_model, output_dir)
            gen_mem_c.run(iters)

        if architecture == "mem-c_ord":
            gen_mem_c_ord = GenVHDLMemC_Ord(self.lgb_model, output_dir)
            gen_mem_c_ord.run(iters)

        if architecture == "mem-c_mem":
            gen_mem_c_mem = GenVHDLMemC_Mem(self.lgb_model, output_dir)
            gen_mem_c_mem.run(iters)

        if architecture == "mem-c_ord_mem":
            gen_mem_c_ord_mem = GenVHDLMemC_Ord_Mem(self.lgb_model, output_dir)
            gen_mem_c_ord_mem.run(iters)

        gen_common = GenVHDLCommon(self.lgb_model, output_dir)
        gen_common.run()

        gen_wrap = GenVHDLWrapper(self.lgb_model, output_dir, architecture)
        gen_wrap.run()

        # Build files generation
        period = 3.0
        generate_build_files(output_dir, "Intel", period)
        generate_build_files(output_dir, "AMD", period)
        print("Done")

    def run_simulation(self, architecture, iters=None):
        if iters is None:
            iters = self.lgb_model.num_iterations
        print("Running simulation...")
        output_dir = os.path.join(self.working_dir, architecture)
        gen_testbench = GenVHDLTestbench(self.lgb_model, output_dir)
        gen_testbench.run()
        error_size = 0.05
        run_simulation = RunSimulation(self.lgb_model, output_dir)
        run_simulation.run(iters, error_size)
        print("Done")

    def debug(self, tree_idx, iters=None):
        if iters is None:
            iters = self.lgb_model.num_iterations

        self.lgb_model.plot_tree(tree_idx)

        test_vec = [0.0 for _ in range(self.lgb_model.num_features)]
        mem_addr_arr = self.lgb_model.simulate_tree(tree_idx, iters, test_vec)
        order_arr = self.lgb_model.get_order_arr(test_vec)
        print(mem_addr_arr)
        print(order_arr)
