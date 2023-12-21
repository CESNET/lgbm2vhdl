import math
import os
import shutil
from fxpmath import Fxp
from importlib.resources import files

from .TemplateFile import TemplateFile
from .Common import clean_dir, get_output_datatype, write_filename_list, get_mem_attrib, get_max_feature_size

class GenVHDLMemC_Mem:
    
    # -----------------------------------------------------------------------------
    def __init__(self, model, output_dir):
        self.model = model
        self.output_dir = os.path.join(output_dir, "lgbm")

    # -----------------------------------------------------------------------------
    def generate_mem_content(self, tree_idx, iters):

        # -----------------------------------------------------------------
        # get memory items info            
        node_addr = 0
        max_diff_addr = 0
        mem_arr = []
        start_addr_list = [node_addr]

        for iter in range(iters):
            tree = self.model.get_tree(tree_idx + iter*self.model.num_classes)        
            stack = [(tree.tree_dict['tree_structure'], -1)]  

            while len(stack) > 0:
                node, par_addr = stack.pop()
                is_split_node = 'split_index' in node.keys()

                if is_split_node:
                    feature = node['split_feature']
                    threshold = node['threshold']
                    stack.append((node['right_child'], node_addr))
                    stack.append((node['left_child'], -1))
                    mem_item = {"type" : "NODE", "feature" : feature, "threshold" : threshold, "next_addr" : 0}
                else:
                    mem_item = {"type" : "LEAF", "value" : node['leaf_value']}

                if par_addr != -1:
                    rec = mem_arr[par_addr]
                    diff_addr = node_addr - par_addr
                    if max_diff_addr < diff_addr:
                        max_diff_addr = diff_addr
                    rec["next_addr"] = diff_addr
                    mem_arr[par_addr] = rec
                
                mem_arr.append(mem_item)
                node_addr += 1
            
            if iter < iters-1:
                start_addr_list.append(node_addr)

        mem_items = node_addr
        next_addr_size = int(math.ceil(math.log2(max_diff_addr+1)))
        instr_addr_size = int(math.ceil(math.log2(mem_items)))

        # -----------------------------------------------------------------
        # generate memory content
        mem_content = ""
        leaf_value_size = 1 + self.g_size + self.i_size + self.m_size + next_addr_size
        instr_size = 1 + 1 + self.g_size + self.i_size + self.m_size + next_addr_size

        for mem_idx in range(len(mem_arr)):
            # print(mem_arr[idx])
                    
            rec_dict = mem_arr[mem_idx]
            node_type = rec_dict['type']
            # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
            # NODE record generation
            if node_type == 'NODE':
                feature = rec_dict['feature']

                int_flag = self.model.feature_df.at[feature,'Int']
                signed_flag = self.model.feature_df.at[feature,'Signed']
                int_size = self.model.feature_df.at[feature,'IntSize']
                dec_size = self.model.feature_df.at[feature,'DecSize']

                threshold = rec_dict['threshold']
                next_addr = rec_dict['next_addr']
                
                if int_flag:
                    threshold = int(math.floor(threshold)) 
                
                threshold_bin = Fxp(threshold, signed_flag, self.m_size, dec_size, rounding='floor')
                signed_logic = '1' if signed_flag else '0'

                item_idx_bin = Fxp(feature, False, self.i_size, 0)
                next_addr_bin = Fxp(next_addr, False, next_addr_size, 0)
                mem_content += "\t\t\"0\" & \"{signed_logic}\" & \"{item_idx}\" & \"{threshold}\" & \"{next_addr}\",\n".format(signed_logic=signed_logic, item_idx=item_idx_bin.bin(), threshold=threshold_bin.bin(), next_addr=next_addr_bin.bin())

            # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
            # LEAF record generation
            else:
                value = rec_dict['value']
                value_bin = Fxp(value, self.model.output_value_quantization[1], leaf_value_size, self.model.output_value_quantization[3])
                mem_content += "\t\t\"1\" & \"{value}\",\n".format(value=value_bin.bin())

        return mem_content, mem_items, next_addr_size, instr_addr_size, instr_size, start_addr_list

    # -----------------------------------------------------------------------------
    def generate_pes(self, pes, iters):

        self.g_size = 0
        self.i_size = math.ceil(math.log2(self.model.num_features))
        self.m_size = get_max_feature_size(self.model)

        output_dir_pes = os.path.join(self.output_dir, "pes")
        if not os.path.exists(output_dir_pes):
            os.makedirs(output_dir_pes)

        template_rom = TemplateFile(["template", "common", "rom.vhd"])
        template_pes = TemplateFile(["template", "mem-c", "mem-c_pe_mt_mem.vhd"])
        shutil.copyfile(files('lgbm2vhdl').joinpath("template", "mem-c", "mem-c_pe_fsm_mt.vhd"), os.path.join(output_dir_pes, "pe_fsm.vhd"))

        for idx in range(pes):
            print("PE", idx)
            mem_content, mem_items, instr_addr_inc_size, instr_addr_size, instr_size, start_addr_list = self.generate_mem_content(idx, iters)            

            # -----------------------------------------------------------------
            # generate Instruction ROM memory
            mem_content = "".join(mem_content.rsplit(',', 1)) # remove , from the last line
            # print(mem_content)

            data_type = "std_logic_vector({size}-1 downto 0)".format(size=instr_size)
            dict = {"idx" : str(idx) + "i" , "addr_size" : instr_addr_size, "data_type" : data_type, "items" : mem_items, "rom_content" : "\n" + mem_content}

            output_file = os.path.join(output_dir_pes, "rom{idx}i.vhd".format(idx=idx))
            template_rom.apply(dict, output_file)

            # -----------------------------------------------------------------
            # generate Start Address ROM memory
            mem_content = ""
            for value in start_addr_list:
                value_bin = Fxp(value, False, instr_addr_size, 0)
                mem_content += "\t\t\"{value}\",\n".format(value=value_bin.bin())

            mem_content = "".join(mem_content.rsplit(',', 1)) # remove , from the last line
            data_type = "std_logic_vector({size}-1 downto 0)".format(size=instr_addr_size)
            # print(mem_content)
            # print(start_addr_list)

            mem_items = len(start_addr_list)
            start_addr_size = int(math.ceil(math.log2(mem_items)))
            if start_addr_size == 0:
                start_addr_size = 1
                srom_inst = ""
            else:
                srom_inst = "ROMs_U : entity work.ROM{idx}s(arch_dist)\n".format(idx=idx)
                srom_inst += "\t\tport map(CLK, start_rom_en, start_rom_addr({high}-1 downto 0), start_rom_data);\n".format(high=start_addr_size)
                dict = {"idx" : str(idx) + "s", "addr_size" : start_addr_size, "data_type" : data_type, "items" : mem_items, "rom_content" : "\n" + mem_content}
                output_file = os.path.join(output_dir_pes, "rom{idx}s.vhd".format(idx=idx))
                template_rom.apply(dict, output_file)

            # -----------------------------------------------------------------
            # generate PE element
            (_, _, int_size, dec_size) = self.model.output_value_quantization

            input_data_type = "t_features"
            output_data_type = get_output_datatype(self.model.output_value_quantization)

            feature_addr_size = math.ceil(math.log2(self.model.num_features))
            feature_data_size = get_max_feature_size(self.model)
            dtype_size = int_size + dec_size            
            dict = {"idx" : idx, "instr_addr_size" : instr_addr_size, "instr_addr_inc_size" : instr_addr_inc_size, "start_addr_size" : start_addr_size, "group_size" : self.g_size, "item_size" : self.i_size, "muxout_size" : self.m_size, 
                    "output_data_type" : output_data_type, "dtype_size" : dtype_size, "dtype_left" : self.model.output_value_quantization[2], "dtype_right" : self.model.output_value_quantization[3], "iters" : iters, "srom_inst" : srom_inst, "signed_mux" : 1,
                    "input_data_type" : input_data_type, "feature_addr_size" : feature_addr_size, "feature_data_size" : feature_data_size}

            output_file = os.path.join(output_dir_pes, "pe{idx}.vhd".format(idx=idx))
            template_pes.apply(dict, output_file)

    # -----------------------------------------------------------------------------
    def get_pe_instances(self, trees, data_type):

        pe_instances = ""

        for idx in range(trees):
            pe_instances += "\tPE{idx}_U : entity work.PE{idx}(behavioral)\n".format(idx=idx)
            pe_instances += "\tport map(CLK, RST, fsm_feature_finish, mi_pe_rd({idx}), mi_pe_raddr({idx}), mi_pe_rdata({idx}), pe_output_en({idx}), CLASS({idx}));\n\n".format(idx=idx)

        return pe_instances
    
    # -----------------------------------------------------------------------------
    def generate_top(self, pes):
        mi_addr_size = math.ceil(math.log2(self.model.num_features))
        mi_data_size = get_max_feature_size(self.model)

        data_type = get_output_datatype(self.model.output_value_quantization)
        pe_instances = self.get_pe_instances(pes, data_type)

        template = TemplateFile(["template", "mem-c_mem", "mem-c_mem_top.vhd"])
        dict = {"pe_instances" : pe_instances, "mi_addr_size" : mi_addr_size, "mi_data_size" : mi_data_size, "num_classes" : self.model.num_classes, "num_features" : self.model.num_features}
        template.apply(dict, output_file = os.path.join(self.output_dir, "top.vhd"))

    # -----------------------------------------------------------------------------
    def generate_files(self, pes, iters):
        l_filenames = [] 
        l_filenames.append(os.path.join(self.output_dir, 'pes', 'pe_fsm.vhd'))

        for idx in range(pes):
            l_filenames.append(os.path.join(self.output_dir, 'pes', 'rom{idx}i.vhd'.format(idx=idx)))
            if iters > 1:
                l_filenames.append(os.path.join(self.output_dir, 'pes', 'rom{idx}s.vhd'.format(idx=idx)))
            l_filenames.append(os.path.join(self.output_dir, 'pes', 'pe{idx}.vhd'.format(idx=idx)))

        l_filenames.append(os.path.join(self.output_dir, 'top.vhd'))

        write_filename_list(self.output_dir, l_filenames)     

    # -----------------------------------------------------------------------------
    def run(self, iters):
        pes = self.model.num_classes
        clean_dir(self.output_dir)
        self.generate_pes(pes, iters)
        self.generate_top(pes)
        self.generate_files(pes, iters)

