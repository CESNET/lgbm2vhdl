import math
import os

from .TemplateFile import TemplateFile
from .Common import clean_dir, get_output_datatype, write_filename_list, get_max_feature_size, get_mem_attrib

class GenVHDLWrapper:
    
    # -----------------------------------------------------------------------------
    def __init__(self, model, source_dir, architecture):
        self.model = model
        self.architecture = architecture
        self.output_dir = os.path.join(source_dir, "wrapper")

    # -----------------------------------------------------------------------------
    def get_features_signals(self):
        feature_regs_rst = ""
        feature_regs_assign = ""

        for idx in range(self.model.num_features):

            name = self.model.feature_df.at[idx,'Name']
            int_flag = self.model.feature_df.at[idx,'Int']
            signed_flag = self.model.feature_df.at[idx,'Signed']
            int_size = self.model.feature_df.at[idx,'IntSize']
            dec_size = self.model.feature_df.at[idx,'DecSize']

            feature_regs_rst += "\t\t\t\treg_feature.{name} <= (others => '0');\n".format(name=name)
            feature_regs_assign += "\t\t\t\tif reg_feature_en({idx}) = '1' then\n".format(idx=idx)
            
            feature_regs_assign += "\t\t\t\t\treg_feature.{name} <= ".format(name=name)

            slv_part = "mi_in_rdata({size} downto 0)".format(size=int_size+dec_size-1)
            if int_flag:
                signed_str = ''if signed_flag else 'un'
                feature_regs_assign += "{signed_str}signed({slv_part});\n".format(signed_str=signed_str, slv_part=slv_part)
            else:
                signed_str = 's'if signed_flag else 'u'
                feature_regs_assign += "to_{signed_str}fixed({slv_part}, {high_idx}, {low_idx});\n".format(signed_str=signed_str, slv_part=slv_part, high_idx=int_size-1, low_idx=-dec_size)

            feature_regs_assign += "\t\t\t\tend if;\n"

        return feature_regs_rst, feature_regs_assign

    # -----------------------------------------------------------------------------
    def generate_wrapper(self):

        mi_in_addr_size = math.ceil(math.log2(self.model.num_features))
        mi_in_data_size = get_max_feature_size(self.model)
        mi_out_addr_size = math.ceil(math.log2(self.model.num_classes))
        (_, _, int_size, dec_size) = self.model.output_value_quantization
        mi_out_data_size = int_size + dec_size

        if self.architecture in {'mem-c_mem', 'mem-c_ord_mem'}:
            template = TemplateFile(["template", "wrapper", "wrapper_mem.vhd"])
            dict = {"mi_in_addr_size" : mi_in_addr_size, "mi_in_data_size" : mi_in_data_size, "mi_out_addr_size" : mi_out_addr_size, "mi_out_data_size" : mi_out_data_size, 
                    "num_features" : self.model.num_features, "num_classes" : self.model.num_classes}
        else:
            template = TemplateFile(["template", "wrapper", "wrapper.vhd"])
            feature_regs_rst, feature_regs_assign = self.get_features_signals()
            dict = {"mi_in_addr_size" : mi_in_addr_size, "mi_in_data_size" : mi_in_data_size, "mi_out_addr_size" : mi_out_addr_size, "mi_out_data_size" : mi_out_data_size, 
                    "num_features" : self.model.num_features, "num_classes" : self.model.num_classes,
                    "feature_regs_rst" : feature_regs_rst, "feature_regs_assign" : feature_regs_assign}

        template.apply(dict, output_file = os.path.join(self.output_dir, "wrapper.vhd"))

    # -----------------------------------------------------------------------------
    def generate_files(self):
        l_filenames = [os.path.join(self.output_dir, "wrapper.vhd")] 
        write_filename_list(self.output_dir, l_filenames)

    # -----------------------------------------------------------------------------
    def run(self):
        clean_dir(self.output_dir)
        self.generate_wrapper()
        self.generate_files()

