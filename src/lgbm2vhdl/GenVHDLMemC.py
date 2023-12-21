import math
import os
import shutil
import numpy as np
from fxpmath import Fxp
from importlib.resources import files

from .TemplateFile import TemplateFile
from .Common import clean_dir, get_output_datatype, write_filename_list, get_mem_attrib

class GenVHDLMemC:
    
    # -----------------------------------------------------------------------------
    def __init__(self, model, output_dir):
        self.model = model
        self.output_dir = os.path.join(output_dir, "lgbm")

    # -----------------------------------------------------------------------------
    def get_groups_of_features(self):
        dict_mapping = {}        
        
        for idx in range(self.model.num_features):
            int_flag = self.model.feature_df.at[idx,'Int']
            signed_flag = self.model.feature_df.at[idx,'Signed']
            int_size = self.model.feature_df.at[idx,'IntSize']
            dec_size = self.model.feature_df.at[idx,'DecSize']            

            if (int_flag, signed_flag, int_size, dec_size) in dict_mapping:
                features = dict_mapping[(int_flag, signed_flag, int_size, dec_size)]
                features.append(idx)
                dict_mapping[(int_flag, signed_flag, int_size, dec_size)] = features
            else:
                dict_mapping[(int_flag, signed_flag, int_size, dec_size)] = [idx]

        self.groups_of_features = dict_mapping
        
        return dict_mapping

    # -----------------------------------------------------------------------------
    def get_max_items(self, dict_mapping):

        max_size = 0
        for item in dict_mapping.values():
            if len(item) > max_size:
                max_size = len(item)

        return max_size

    # -----------------------------------------------------------------------------
    def get_mux_size(self, dict_mapping):

        max_size = 0
        for key in dict_mapping:
            size = key[2] + key[3] # Int_size + Dec_size
            
            if size > max_size:
                max_size = size

        return max_size
    
    # -----------------------------------------------------------------------------
    def get_item_mux_inst(self):
        item_mux_inst = ""
        output_signals = ""
        for idx, key in enumerate(self.groups_of_features):
            values = self.groups_of_features[key]

            inputs = ""
            cases = ""
            sel_item_size = int(math.ceil(math.log2(len(values))))

            for val_id, val in enumerate(values):
                name = self.model.feature_df.at[val,'Name']
                inputs += "INPUTS." + name + ', '
                if val_id < len(values)-1:
                    val_id_bin = f"{val_id:0{sel_item_size}b}"
                    cases += "\t\t\twhen \"{val_id}\" => mux_out{idx} <= INPUTS.{name};\n".format(val_id=val_id_bin, idx=idx, name=name)
                else:
                    cases += "\t\t\twhen others => mux_out{idx} <= INPUTS.{name};\n".format(idx=idx, name=name)

            item_mux_inst += '\titem_mux_{idx} : process({inputs}SEL_ITEM)\n\tbegin\n'.format(idx=idx, inputs=inputs)
            item_mux_inst += '\t\tcase SEL_ITEM({sel_item_size}-1 downto 0) is \n'.format(sel_item_size=sel_item_size)
            item_mux_inst += cases
            item_mux_inst += '\t\tend case;\n'.format(idx=idx)
            item_mux_inst += '\tend process item_mux_{idx};\n\n'.format(idx=idx)

            int_flag = key[0]
            signed_flag = key[1]
            int_size = key[2]
            dec_size = key[3]

            if int_flag:
                signed_str = ''if signed_flag else 'un'
                output_signals += '\tsignal mux_out{idx} : {signed_str}signed({higher} downto {lower});\n'.format(idx=idx, signed_str=signed_str, higher=int_size+dec_size-1, lower=0)
            else:
                signed_str = 's'if signed_flag else 'u'
                output_signals += '\tsignal mux_out{idx} : {signed_str}fixed({higher} downto -{lower});\n'.format(idx=idx, signed_str=signed_str, higher=int_size-1, lower=dec_size)

        return item_mux_inst, output_signals

    # -----------------------------------------------------------------------------
    def get_group_mux_inst(self, i_size, g_size, m_size):
        group_mux_inst = ""

        inputs = ""
        cases = ""

        for idx, key in enumerate(self.groups_of_features):
            int_flag = key[0]
            signed_flag = key[1]

            inputs += "mux_out{idx}, ".format(idx=idx)

            if signed_flag:
                signed_str = "signed"
            else:
                signed_str = "unsigned"

            if int_flag:
                slv_output = "mux_out{idx}".format(idx=idx)
            else:
                slv_output = "to_slv(mux_out{idx})".format(idx=idx)

            output = "std_logic_vector(resize({signed_str}({slv_output}), {m_size}))".format(signed_str=signed_str, slv_output=slv_output, m_size=m_size)

            if idx < len(self.groups_of_features)-1:
                idx_bin = f"{idx:0{g_size}b}"
                cases += "\t\t\twhen \"{idx_bin}\" => OUTPUT <= {output};\n".format(idx_bin=idx_bin, output=output)
            else:
                if g_size > 0:
                    cases += "\t\t\twhen others => OUTPUT <= {output};\n".format(output=output)
                else:
                    cases += "\tOUTPUT <= {output};\n".format(output=output)

        if g_size > 0:
            group_mux_inst += '\tgroup_mux : process({inputs}SEL_ITEM)\n\tbegin\n'.format(inputs=inputs)
            group_mux_inst += '\t\tcase SEL_ITEM({g_size}+{i_size}-1 downto {i_size}) is \n'.format(g_size=g_size, i_size=i_size)
            group_mux_inst += cases
            group_mux_inst += '\t\tend case;\n'
            group_mux_inst += '\tend process group_mux;\n\n'
        else:
            group_mux_inst += cases

        return group_mux_inst

    # -----------------------------------------------------------------------------
    def generate_mux(self):
        dict_mapping = self.get_groups_of_features()
        
        i_size = int(math.ceil(math.log2(self.get_max_items(dict_mapping))))
        g_size = int(math.ceil(math.log2(len(dict_mapping))))
        m_size = self.get_mux_size(dict_mapping)
        item_mux_inst, output_signals = self.get_item_mux_inst()
        group_mux_inst = self.get_group_mux_inst(i_size, g_size, m_size)

        dict = {"m_size" : m_size, "g_size" : g_size, "i_size" : i_size, "item_mux_inst" : item_mux_inst, "output_signals" : output_signals, "group_mux_inst" : group_mux_inst, "datatype" : "t_features", "package" : ""}

        template = TemplateFile(["template",  "mem-c", "mem-c_mux.vhd"])
        output_file = os.path.join(self.output_dir, "mux.vhd")
        template.apply(dict, output_file)

        self.i_size = i_size
        self.g_size = g_size
        self.m_size = m_size

    # -----------------------------------------------------------------------------
    def get_item_group_idx(self, feature):

        for group_idx, key in enumerate(self.groups_of_features):
            values = self.groups_of_features[key]
            for item_idx, val in enumerate(values):
                if (val == feature):
                    return item_idx, group_idx

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

                item_idx, group_idx = self.get_item_group_idx(feature)
                item_idx_bin = Fxp(item_idx, False, self.i_size, 0)
                next_addr_bin = Fxp(next_addr, False, next_addr_size, 0)

                if self.g_size > 0:
                    group_idx_bin = Fxp(group_idx, False, self.g_size, 0)
                    mem_content += "\t\t\"0\" & \"{signed_logic}\" & \"{group_idx}\" & \"{item_idx}\" & \"{threshold}\" & \"{next_addr}\",\n".format(signed_logic=signed_logic, group_idx=group_idx_bin.bin(), item_idx=item_idx_bin.bin(), threshold=threshold_bin.bin(), next_addr=next_addr_bin.bin())
                else:
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

        output_dir_pes = os.path.join(self.output_dir, "pes")
        if not os.path.exists(output_dir_pes):
            os.makedirs(output_dir_pes)

        template_rom = TemplateFile(["template", "common", "rom.vhd"])
        template_pes = TemplateFile(["template", "mem-c", "mem-c_pe_mt.vhd"])
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
                srom_inst = "ROMs_U : entity work.ROM{idx}s\n".format(idx=idx)
                srom_inst += "\t\tport map(CLK, start_rom_en, start_rom_addr({high}-1 downto 0), start_rom_data);\n".format(high=start_addr_size)
                dict = {"idx" : str(idx) + "s", "addr_size" : start_addr_size, "data_type" : data_type, "items" : mem_items, "rom_content" : "\n" + mem_content}
                output_file = os.path.join(output_dir_pes, "rom{idx}s.vhd".format(idx=idx))
                template_rom.apply(dict, output_file)

            # -----------------------------------------------------------------
            # generate PE element
            (_, _, int_size, dec_size) = self.model.output_value_quantization

            input_data_type = "t_features"
            output_data_type = get_output_datatype(self.model.output_value_quantization)

            dtype_size = int_size + dec_size            
            dict = {"idx" : idx, "instr_addr_size" : instr_addr_size, "instr_addr_inc_size" : instr_addr_inc_size, "start_addr_size" : start_addr_size, "group_size" : self.g_size, "item_size" : self.i_size, "muxout_size" : self.m_size, 
                    "output_data_type" : output_data_type, "dtype_size" : dtype_size, "dtype_left" : self.model.output_value_quantization[2], "dtype_right" : self.model.output_value_quantization[3], "iters" : iters, "srom_inst" : srom_inst, "signed_mux" : 1,
                    "package" : "", "input_data_type" : input_data_type}

            output_file = os.path.join(output_dir_pes, "pe{idx}.vhd".format(idx=idx))
            template_pes.apply(dict, output_file)

    # -----------------------------------------------------------------------------
    def get_pe_instances(self, trees, data_type):

        pe_instances = ""

        for idx in range(trees):
            pe_instances += "\tPE{idx}_U : entity work.PE{idx}(behavioral)\n".format(idx=idx)
            pe_instances += "\tport map(CLK, RST, FEATURES_EN, FEATURES, pe_output_en({idx}), CLASS({idx}));\n\n".format(idx=idx)

        return pe_instances
    
    # -----------------------------------------------------------------------------
    def generate_top(self, pes):
        template = TemplateFile(["template", "mem-c", "mem-c_top.vhd"])

        data_type = get_output_datatype(self.model.output_value_quantization)
        
        pe_instances = self.get_pe_instances(pes, data_type)

        dict = {"pe_instances" : pe_instances,
                "num_pes" : pes, "num_trees" : self.model.num_trees, "num_classes" : self.model.num_classes, "num_iters" : self.model.num_iterations}

        template.apply(dict, output_file = os.path.join(self.output_dir, "top.vhd"))

    # -----------------------------------------------------------------------------
    def generate_files(self, pes, iters):
        l_filenames = [] 
        l_filenames.append(os.path.join(self.output_dir, 'mux.vhd'))
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
        self.generate_mux()
        self.generate_pes(pes, iters)
        self.generate_top(pes)
        self.generate_files(pes, iters)

