import math
import os
import shutil
from importlib.resources import files

from .TemplateFile import TemplateFile
from .Common import clean_dir, get_max_feature_size, generate_all_files

class GenVHDLTestbench:
    
    # -----------------------------------------------------------------------------
    def __init__(self, model, source_dir):
        self.model = model
        self.source_dir = source_dir
        self.output_dir = os.path.join(source_dir, "sim")

    # -----------------------------------------------------------------------------
    def generate_testbench(self):
        
        mi_in_addr_size = math.ceil(math.log2(self.model.num_features))
        mi_in_data_size = get_max_feature_size(self.model)
        mi_out_addr_size = math.ceil(math.log2(self.model.num_classes))
        (_, _, int_size, dec_size) = self.model.output_value_quantization
        mi_out_data_size = int_size + dec_size

        template = TemplateFile(["template", "sim", "testbench.vhd"])

        dict = {"mi_in_addr_size" : mi_in_addr_size, "mi_in_data_size" : mi_in_data_size, "mi_out_addr_size" : mi_out_addr_size, "mi_out_data_size" : mi_out_data_size, 
                "num_classes" : self.model.num_classes}

        template.apply(dict, output_file = os.path.join(self.output_dir, "testbench.vhd"))

    # -----------------------------------------------------------------------------
    def run(self):
        clean_dir(self.output_dir)
        self.generate_testbench()

        # Generate testbench files
        generate_all_files(self.source_dir, self.output_dir)
        shutil.copyfile(files('lgbm2vhdl').joinpath("template", "sim", "vcom.do"), os.path.join(self.output_dir, "vcom.do"))
        shutil.copyfile(files('lgbm2vhdl').joinpath("template", "sim", "vsim.do"), os.path.join(self.output_dir, "vsim.do"))
        shutil.copyfile(files('lgbm2vhdl').joinpath("template", "sim", "wave.do"), os.path.join(self.output_dir, "wave.do"))
