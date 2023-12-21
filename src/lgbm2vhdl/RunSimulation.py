import os
import numpy as np
import lightgbm as lgb
import pandas as pd
import shutil
import subprocess
from fxpmath import Fxp

from .Common import clean_dir, get_max_feature_size

class RunSimulation:
    
    # -----------------------------------------------------------------------------
    def __init__(self, model, source_dir):
        self.model = model
        self.source_dir = source_dir
        self.sim_dir = os.path.join(source_dir, "sim")

    # -----------------------------------------------------------------------------
    def save_input(self, file_name, vector):
        mi_in_data_size = get_max_feature_size(self.model)
        
        bin_vec = []
        for idx in range(self.model.num_features):
            signed_flag = self.model.feature_df.at[idx,'Signed']
            dec_size = self.model.feature_df.at[idx,'DecSize']

            x = Fxp(vector[idx], signed_flag, mi_in_data_size, dec_size, rounding='floor')
            bin_vec.append(x.bin())

        with open(file_name, 'w') as fw:
            lines = '\n'.join(bin_vec)
            fw.write(lines)

    # -----------------------------------------------------------------------------
    def save_reference_output(self, file_name, vector):
        with open(file_name, 'w') as fw:
            str_vec = [str(i) for i in vector]
            lines = '\n'.join(str_vec)
            fw.write(lines)

    # -----------------------------------------------------------------------------
    def generate_test_vectors(self, iters):
        print("Test vector generation...")
        test_dir = os.path.join(self.sim_dir, 'test_vectors')
        clean_dir(test_dir)

        self.test_vec = pd.Series(data=[0.0 for _ in range(self.model.num_features)], index=[str(i) for i in range(self.model.num_features)])
        self.iters = iters
        # print(type(test_vec))
        # print(test_vec)

        itX = self.model.lgb_model.predict(self.test_vec, start_iteration=0, num_iteration=iters, raw_score=True)
        # print(it0)

        input_file = os.path.join(test_dir, 'input.txt')
        self.save_input(input_file, self.test_vec)
        output_file = os.path.join(test_dir, 'output_golden.txt')
        self.save_reference_output(output_file, itX[0])

    # -----------------------------------------------------------------------------
    def run_simulation(self, compile=False):

        shutil.copyfile(os.path.join(self.sim_dir, 'test_vectors', 'input.txt'), os.path.join(self.sim_dir, 'input_data.txt'))

        print("Simulation...")
        if compile:
            subprocess.run(['vsim', '-c', '-do', 'vcom.do'], cwd=self.sim_dir)
        subprocess.run(['vsim', '-c', '-do', 'vsim.do'], cwd=self.sim_dir)

    # -----------------------------------------------------------------------------
    def load_reference_output(self, file_name):
        with open(file_name, 'r') as fr:
            lines = fr.readlines()
            numbers =[float(i.strip()) for i in lines]

        return numbers

    # -----------------------------------------------------------------------------
    def load_simulation_output(self, file_name, output_value_quantizaton):
        with open(file_name, 'r') as fr:
            lines = fr.readlines()
            str_numbers =[i.strip() for i in lines]

            numbers = []
            for item in str_numbers:
                item_str = "0b" + item
                x = Fxp(item_str, output_value_quantizaton[1], output_value_quantizaton[2]+output_value_quantizaton[3], output_value_quantizaton[3])
                numbers.append(x.astype(float))

        return numbers

    # -----------------------------------------------------------------------------
    def compare_outputs(self, error_size):
        reference_file = os.path.join(self.sim_dir, 'test_vectors', 'output_golden.txt')
        simulation_file = os.path.join(self.sim_dir, 'output_data.txt')
        
        ref_vector = self.load_reference_output(reference_file)
        # print(ref_vector)

        sim_vector = self.load_simulation_output(simulation_file, self.model.output_value_quantization)
        # print(sim_vector)

        result = True
        for i, j in zip(ref_vector, sim_vector):
            err = abs(i-j)
            if err > error_size:
                result = False

        return result, ref_vector, sim_vector

    # -----------------------------------------------------------------------------
    def print_result(self, ref_vector, sim_vector, error_size):

        iters_results = [ [] for _ in range(len(ref_vector)) ]

        for i in range(self.iters):
            itX = self.model.lgb_model.predict(self.test_vec, start_iteration=i, num_iteration=1, raw_score=True)
            for idx, item in enumerate(itX[0]):
                iters_results[idx].append(item)

        for ref, sim, iter_vals in zip(ref_vector, sim_vector, iters_results):
            err = abs(ref-sim)
            result_str = "OK " if err <= error_size else "ERR"
            iter_str = ["{0:+0.5f}".format(i) for i in iter_vals]
            print(result_str, "{0:+0.5f} {1:+0.5f} {2:+0.5f}".format(ref, sim, err), iter_str)

    # -----------------------------------------------------------------------------
    def evaluate_results(self, error_size):

        result, ref_vector, sim_vector = self.compare_outputs(error_size)

        if not result:
            self.print_result(ref_vector, sim_vector, error_size)
        else:
            print('Test result: OK')

    # -----------------------------------------------------------------------------
    def run(self, iters, error_size):
        self.generate_test_vectors(iters)
        self.run_simulation(compile=True)
        self.evaluate_results(error_size)
