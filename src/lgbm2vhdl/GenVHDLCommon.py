import os
import shutil
from importlib.resources import files

from .TemplateFile import TemplateFile
from .Common import clean_dir, write_filename_list, get_output_datatype, get_features_ports, get_mem_attrib

class GenVHDLCommon:
    
    # -----------------------------------------------------------------------------
    def __init__(self, model, source_dir):
        self.model = model
        self.output_dir = os.path.join(source_dir, "common")

    # -----------------------------------------------------------------------------
    def generate_package(self):
        template = TemplateFile(["template", "common", "dtype_pkg.vhd"])
        
        data_type =  get_output_datatype(self.model.output_value_quantization)
        features = get_features_ports(self.model)
        
        dict = {"features" : features, "data_type" : data_type, "num_classes" : self.model.num_classes, "num_iters" : self.model.num_iterations}
        template.apply(dict, os.path.join(self.output_dir, "dtype_pkg.vhd"))

    # -----------------------------------------------------------------------------
    def generate_mem(self):
        shutil.copyfile(files('lgbm2vhdl').joinpath("template", "common", "dp_ram.vhd"), os.path.join(self.output_dir, "dp_ram.vhd"))

    # -----------------------------------------------------------------------------
    def generate_files(self):
        l_filenames = [] 
        l_filenames.append(os.path.join(self.output_dir, 'dtype_pkg.vhd'))
        l_filenames.append(os.path.join(self.output_dir, 'cnt_fsm.vhd'))
        l_filenames.append(os.path.join(self.output_dir, 'barrier.vhd'))
        l_filenames.append(os.path.join(self.output_dir, 'dp_ram.vhd'))
        write_filename_list(self.output_dir, l_filenames)

    # -----------------------------------------------------------------------------
    def run(self):
        clean_dir(self.output_dir)
        self.generate_package()
        self.generate_mem()
        shutil.copyfile(files('lgbm2vhdl').joinpath("template", "common", "cnt_fsm.vhd"), os.path.join(self.output_dir, "cnt_fsm.vhd"))
        shutil.copyfile(files('lgbm2vhdl').joinpath("template", "common", "barrier.vhd"), os.path.join(self.output_dir, "barrier.vhd"))
        self.generate_files()
