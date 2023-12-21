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
from importlib.resources import files

# -----------------------------------------------------------------------------
def run(output_dir, model_filename, quantizaton_filename, architecture, iters, gen_vhdl, simulation, build, debug):
    print("Running")

    # -------------------------------------------------------------------------
    # Architecture generation
    # -------------------------------------------------------------------------
    if gen_vhdl:
        # Model loading
        lgb_model = LGBModel(model_filename, quantizaton_filename)
        # lgb_model.print_info()

        if architecture == "mem-c":
            gen_mem_c = GenVHDLMemC(lgb_model, output_dir)
            gen_mem_c.run(iters)

        if architecture == "mem-c_ord":
            gen_mem_c_ord = GenVHDLMemC_Ord(lgb_model, output_dir)
            gen_mem_c_ord.run(iters)

        if architecture == "mem-c_mem":
            gen_mem_c_mem = GenVHDLMemC_Mem(lgb_model, output_dir)
            gen_mem_c_mem.run(iters)

        if architecture == "mem-c_ord_mem":
            gen_mem_c_ord_mem = GenVHDLMemC_Ord_Mem(lgb_model, output_dir)
            gen_mem_c_ord_mem.run(iters)

        gen_common = GenVHDLCommon(lgb_model, output_dir)
        gen_common.run()

        gen_wrap = GenVHDLWrapper(lgb_model, output_dir, architecture)
        gen_wrap.run()

    # -------------------------------------------------------------------------
    # Simulation
    # -------------------------------------------------------------------------
    if simulation:
        gen_testbench = GenVHDLTestbench(lgb_model, output_dir)
        gen_testbench.run()
        error_size = 0.05
        run_simulation = RunSimulation(lgb_model, output_dir)
        run_simulation.run(iters, error_size)

    # -------------------------------------------------------------------------
    # Debug
    # -------------------------------------------------------------------------
    if debug:
        tree_idx = 2
        lgb_model = LGBModel(model_filename, quantizaton_filename)
        test_vec = [0.0 for _ in range(lgb_model.num_features)]
        # lgb_model.plot_tree(idx)
        mem_addr_arr = lgb_model.simulate_tree(tree_idx, iters, test_vec)
        order_arr = lgb_model.get_order_arr(test_vec)
        print(mem_addr_arr)
        print(order_arr)

    # -------------------------------------------------------------------------
    # Build
    # -------------------------------------------------------------------------
    if build:
        period = 3.0
        generate_build_files(output_dir, "Intel", period)
        generate_build_files(output_dir, "AMD", period)

    print("Finished")
