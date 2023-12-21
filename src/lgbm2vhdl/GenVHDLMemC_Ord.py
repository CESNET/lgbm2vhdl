import math
import os
import shutil
from fxpmath import Fxp
from importlib.resources import files

from .TemplateFile import TemplateFile
from .Common import clean_dir, get_output_datatype, write_filename_list, get_threshold_index, get_mem_attrib

class GenVHDLMemC_Ord:
    
    # -----------------------------------------------------------------------------
    def __init__(self, model, output_dir):
        self.model = model
        self.output_dir = os.path.join(output_dir, "lgbm")

    # -----------------------------------------------------------------------------
    def get_groups_of_features(self):
        dict_mapping = {}        
        
        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # Find features of the same type
        for idx in range(self.model.num_features):
            int_flag = self.model.feature_df.at[idx,'Int']
            signed_flag = self.model.feature_df.at[idx,'Signed']
            int_size = self.model.feature_df.at[idx,'IntSize']
            dec_size = self.model.feature_df.at[idx,'DecSize']
            thresholds = len(self.model.lists_of_thresholds[idx])
            if thresholds > 0:
                if (int_flag, signed_flag, int_size, dec_size) in dict_mapping:
                    features = dict_mapping[(int_flag, signed_flag, int_size, dec_size)]
                    features.append(idx)
                    dict_mapping[(int_flag, signed_flag, int_size, dec_size)] = features
                else:
                    dict_mapping[(int_flag, signed_flag, int_size, dec_size)] = [idx]

        self.groups_of_features = dict_mapping

        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # Split features of the same type to lists of max length
        lists_of_cmp_features = []
        max_features = 16
        for key in dict_mapping:
            features = dict_mapping[key]
            
            while len(features) > 0:
                if len(features):
                    lists_of_cmp_features.append(features[0:max_features])
                    features = features[max_features:]
                else:
                    lists_of_cmp_features.append(features)
                    features = []

        # print(dict_mapping)
        # print(lists_of_cmp_features)

        return lists_of_cmp_features

    # -----------------------------------------------------------------------------
    def generate_group_bin_search(self, iters):
        self.model.get_uniq_model_thresholds()

        # Create output directory if not exists        
        output_dir_comparators = os.path.join(self.output_dir, "comparators")
        if not os.path.exists(output_dir_comparators):
            os.makedirs(output_dir_comparators)

        self.lists_of_cmp_features = self.get_groups_of_features()

        template_rom = TemplateFile(["template", "common", "rom.vhd"])

        for c_idx, cmp_features in enumerate(self.lists_of_cmp_features):
            print("Feature Comparator Group", c_idx)       
            
            interface = []
            output_assign = []
            max_addr_size = 0
            rom_inst = ""
            stride_list = []
            feature_arr_inst = ""

            mem_content_list = []
            start_addr_list = []
            final_items_list = []
            start_addr = 0
            final_items = 0

            for f_idx, f_id in enumerate(cmp_features):
                start_addr += final_items
                start_addr_list.append(start_addr)
                list_of_thresholds = self.model.lists_of_thresholds[f_id]
                # print(f_id, list_of_thresholds)

                int_flag = self.model.feature_df.at[f_id,'Int']
                signed_flag = self.model.feature_df.at[f_id,'Signed']
                int_size = self.model.feature_df.at[f_id,'IntSize']
                dec_size = self.model.feature_df.at[f_id,'DecSize']
                # print(int_flag, signed_flag, int_size, dec_size)

                feature_arr_inst += "\tfeature_arr({idx}) <= F{f_id};\n".format(idx=f_idx, f_id=f_id)

                if int_flag:
                    signed_str = ''if signed_flag else 'un'
                    data_type = "{signed_str}signed({higher} downto {lower})".format(signed_str=signed_str, higher=int_size+dec_size-1, lower=0)
                    datatype_conv = "{signed_str}signed(RDATA)".format(signed_str=signed_str)
                else:
                    signed_str = 's'if signed_flag else 'u'
                    data_type = "{signed_str}fixed({higher} downto -{lower})".format(signed_str=signed_str, higher=int_size-1, lower=dec_size)
                    datatype_conv = "to_{signed_str}fixed(RDATA, {high_idx}, {low_idx})".format(signed_str=signed_str, high_idx=int_size-1, low_idx=-dec_size)

                for i,t in enumerate(list_of_thresholds):
                    x = Fxp(t, signed_flag, int_size+dec_size, dec_size, rounding='floor')
                    item = '\"{threshold}\"'.format(threshold=x.bin())
                    mem_content_list.append(item)

                items = len(list_of_thresholds)
                final_items = int(pow(2.0, int(math.ceil(math.log2(items)))))

                if final_items == 1:
                    final_items = 2
                final_items_list.append(final_items)

                for i in range(items, final_items):
                    x_max = Fxp(x.upper, signed_flag, int_size+dec_size, dec_size)
                    mem_content_list.append('\"{threshold}\"'.format(threshold=x_max.bin()))

                # print (items, final_items, mem_content_list)

                stride_list.append(int(final_items/2))
                block_addr_size = int(math.ceil(math.log2(final_items)))
                
                if max_addr_size < block_addr_size:
                    max_addr_size = block_addr_size

                interface.append("\n\tF{idx}\t\t\t: in {data_type}".format(idx=f_id, data_type=data_type))
                interface.append("F{idx}_ORD\t\t: out std_logic_vector({size} downto 0)".format(idx=f_id, size=block_addr_size))
                interface.append("F{idx}_ORD_EN\t: out std_logic".format(idx=f_id))
                output_assign.append("F{idx}_ORD    <= wdata({size} downto 0);".format(idx=f_id, size=block_addr_size))
                output_assign.append("F{idx}_ORD_EN <= feature_en({ofs});".format(idx=f_id, ofs=f_idx))

            mem_items = len(mem_content_list)
            mem_addr_size = int(math.ceil(math.log2(mem_items)))
            mem_content_str = ", ".join(mem_content_list)

            dict = {"idx" : str(c_idx)+"t", "addr_size" : mem_addr_size, "data_type" : data_type, "items" : mem_items, "rom_content" : mem_content_str}
            output_file = os.path.join(output_dir_comparators, "rom{idx}t.vhd".format(idx=c_idx))
            template_rom.apply(dict, output_file)
                
            stride_content = []
            for stride in stride_list:
                x = Fxp(stride, False, max_addr_size, 0)
                stride_content.append('\"{stride}\"'.format(stride=x.bin()))

            # print("Final Items", final_items_list)
            # print("Start Addr", start_addr_list)
            start_content = []
            for start in start_addr_list:
                x = Fxp(start, False, mem_addr_size, 0)
                start_content.append('\"{start}\"'.format(start=x.bin()))

            num_features = len(cmp_features)
            feature_addr_size = int(math.ceil(math.log2(num_features)))
            feature_data_size = int_size + dec_size
            stride_content_str = ", ".join(stride_content)
            start_content_str = ", ".join(start_content)

            output_file = os.path.join(output_dir_comparators, "cmp_ord_core{idx}.vhd".format(idx=c_idx))
            template_cmp_core = TemplateFile(["template", "cmp_ord", "cmp_ord_group_mt_core.vhd"])
            dict = {"idx" : str(c_idx), "addr_size" : mem_addr_size, "stride_size" : max_addr_size, "data_type" : data_type, "rom_inst" : rom_inst,
                    "num_features" : num_features, "feature_addr_size" : feature_addr_size, "feature_data_size" : feature_data_size, "stride_content" : stride_content_str, "start_content" : start_content_str, 'datatype_conv' : datatype_conv}
            template_cmp_core.apply(dict, output_file)

            interface_str = ";\n\t".join(interface)
            output_assign_str = "\n\t".join(output_assign)

            output_file = os.path.join(output_dir_comparators, "cmp_ord{idx}.vhd".format(idx=c_idx))
            template_cmp = TemplateFile(["template", "cmp_ord", "cmp_ord_group_mt.vhd"])
            dict = {"idx" : str(c_idx), "stride_size" : max_addr_size, "data_type" : data_type, "interface" : interface_str, "output_assign" : output_assign_str,
                    "num_features" : num_features, "feature_addr_size" : feature_addr_size, "feature_data_size" : feature_data_size, "feature_arr_inst" : feature_arr_inst}
            template_cmp.apply(dict, output_file)

        shutil.copyfile(files('lgbm2vhdl').joinpath("template", "cmp_ord", "cmp_ord_fsm_group_mt.vhd"), os.path.join(output_dir_comparators, "cmp_ord_fsm.vhd"))

    # -----------------------------------------------------------------------------
    def get_groups_of_mux_size(self):
        dict_mapping = {}        

        for idx, t_list in enumerate(self.model.lists_of_thresholds):
            items = (len(t_list)) 
            if items > 0:
                if items > 1:
                    mux_size = int(math.ceil(math.log2(items)))+1
                else:
                    mux_size = 2
                # print(idx, items, mux_size)

                if mux_size in dict_mapping:
                    features = dict_mapping[mux_size]
                    features.append(idx)
                    dict_mapping[mux_size] = features
                else:
                    dict_mapping[mux_size] = [idx]

        self.groups_of_features = dict_mapping
        # print(dict_mapping)

        return dict_mapping

    # -----------------------------------------------------------------------------
    def get_max_items(self, dict_mapping):

        max_size = 0
        for item in dict_mapping.values():
            if len(item) > max_size:
                max_size = len(item)

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

            output_signals += '\tsignal mux_out{idx} : std_logic_vector({higher}-1 downto 0);\n'.format(idx=idx, higher=key)

        return item_mux_inst, output_signals

    # -----------------------------------------------------------------------------
    def get_group_mux_inst(self, i_size, g_size, m_size):
        group_mux_inst = ""

        inputs = ""
        cases = ""

        for idx, key in enumerate(self.groups_of_features):

            inputs += "mux_out{idx}, ".format(idx=idx)
            output = "std_logic_vector(resize(unsigned(mux_out{idx}), {m_size}))".format(idx=idx, m_size=m_size)

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
        dict_mapping = self.get_groups_of_mux_size()
        
        i_size = int(math.ceil(math.log2(self.get_max_items(dict_mapping))))
        g_size = int(math.ceil(math.log2(len(dict_mapping))))
        m_size = max(dict_mapping.keys())
        item_mux_inst, output_signals = self.get_item_mux_inst()
        group_mux_inst = self.get_group_mux_inst(i_size, g_size, m_size)

        package = "use work.dtype_memc_ord_pkg.all;"
        dict = {"m_size" : m_size, "g_size" : g_size, "i_size" : i_size, "item_mux_inst" : item_mux_inst, "output_signals" : output_signals, "group_mux_inst" : group_mux_inst, "datatype" : "t_cmp_ord", "package" : package}

        template = TemplateFile(["template", "mem-c", "mem-c_mux.vhd"])
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
        leaf_value_size = self.g_size + self.i_size + self.m_size + next_addr_size
        instr_size = 1 + self.g_size + self.i_size + self.m_size + next_addr_size

        for mem_idx in range(len(mem_arr)):
            # print(mem_arr[idx])
                    
            rec_dict = mem_arr[mem_idx]
            node_type = rec_dict['type']
            # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
            # NODE record generation
            if node_type == 'NODE':
                feature = rec_dict['feature']
                threshold = rec_dict['threshold']
                next_addr = rec_dict['next_addr']
                
                int_flag = self.model.feature_df.at[feature,'Int']
                if int_flag:
                    threshold = int(math.floor(threshold)) 
                
                threshold_idx = get_threshold_index(self.model, feature, threshold)
                threshold_idx_fxp = Fxp(threshold_idx, False, self.m_size, 0)

                item_idx, group_idx = self.get_item_group_idx(feature)
                item_idx_bin = Fxp(item_idx, False, self.i_size, 0)
                next_addr_bin = Fxp(next_addr, False, next_addr_size, 0)

                if self.g_size > 0:
                    group_idx_bin = Fxp(group_idx, False, self.g_size, 0)
                    mem_content += "\t\t\"0\" & \"{group_idx}\" & \"{item_idx}\" & \"{threshold}\" & \"{next_addr}\",\n".format(group_idx=group_idx_bin.bin(), item_idx=item_idx_bin.bin(), threshold=threshold_idx_fxp.bin(), next_addr=next_addr_bin.bin())
                else:
                    mem_content += "\t\t\"0\" & \"{item_idx}\" & \"{threshold}\" & \"{next_addr}\",\n".format(item_idx=item_idx_bin.bin(), threshold=threshold_idx_fxp.bin(), next_addr=next_addr_bin.bin())

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

            input_data_type = "t_cmp_ord"
            output_data_type = get_output_datatype(self.model.output_value_quantization)

            package = "use work.dtype_memc_ord_pkg.all;"
            dtype_size = int_size + dec_size            
            dict = {"idx" : idx, "instr_addr_size" : instr_addr_size, "instr_addr_inc_size" : instr_addr_inc_size, "start_addr_size" : start_addr_size, "group_size" : self.g_size, "item_size" : self.i_size, "muxout_size" : self.m_size, 
                    "output_data_type" : output_data_type, "dtype_size" : dtype_size, "dtype_left" : self.model.output_value_quantization[2], "dtype_right" : self.model.output_value_quantization[3], "iters" : iters, "srom_inst" : srom_inst, "signed_mux" : 0,
                    "package" : package, "input_data_type" : input_data_type}

            output_file = os.path.join(output_dir_pes, "pe{idx}.vhd".format(idx=idx))
            template_pes.apply(dict, output_file)

    # -----------------------------------------------------------------------------
    def get_cmp_instances_group(self):

        cmp_instances = ""
        cmp_count = 0

        for c_idx, item in enumerate(self.lists_of_cmp_features):
            
            cmp_signals = []
            for f_idx, f_id in enumerate(item):

                name = self.model.feature_df.at[f_id,'Name']
                cmp_signals.append("FEATURES.{name}, cmp_output.{name}, cmp_output_en({idx})".format(name=name, idx=cmp_count))
                cmp_count += 1

            cmp_signals_str = ", ".join(cmp_signals)
            cmp_instances += "\tCMP_ORDER{idx}_U : entity work.CMP_ORDER{idx}(behavioral)\n".format(idx=c_idx)
            cmp_instances += "\tport map(CLK, RST, FEATURES_EN, {cmp_signals});\n\n".format(cmp_signals=cmp_signals_str)

        return cmp_instances, cmp_count

    # -----------------------------------------------------------------------------
    def get_cmp_instances(self):

        cmp_instances = ""
        cmp_count = 0

        for idx, item in enumerate(self.model.lists_of_thresholds):
            if len(item) > 0:
                cmp_instances += "\tCMP_ORDER{idx}_U : entity work.CMP_ORDER{idx}(behavioral)\n".format(idx=idx)
                name = self.model.feature_df.at[idx,'Name']
                cmp_instances += "\tport map(CLK, RST, FEATURES_EN, FEATURES.{name}, cmp_output_en({idx_fin}), cmp_output.{name});\n\n".format(idx=idx, name=name, idx_fin=cmp_count)
                cmp_count += 1

        return cmp_instances, cmp_count

    # -----------------------------------------------------------------------------
    def get_pkg_signals(self):

        pkg_signals = ""
        for idx, item in enumerate(self.model.lists_of_thresholds):
            if len(item) > 0:
                name = self.model.feature_df.at[idx,'Name']
                if len(item) > 1:
                    cmp_ord_size = int(math.ceil(math.log2(len(item)))) + 1
                else:
                    cmp_ord_size = 2
                pkg_signals += "\t{name} : std_logic_vector({size}-1 downto 0);\n".format(name=name, size=cmp_ord_size)

        return pkg_signals

    # -----------------------------------------------------------------------------
    def get_pe_instances(self, trees, data_type):

        pe_instances = ""

        for idx in range(trees):
            pe_instances += "\tPE{idx}_U : entity work.PE{idx}(behavioral)\n".format(idx=idx)
            pe_instances += "\tport map(CLK, RST, pe_input_en, pe_input, pe_output_en({idx}), CLASS({idx}));\n\n".format(idx=idx)

        return pe_instances

    # -----------------------------------------------------------------------------
    def generate_cmp_ord_barrier(self):

        regs_rst = ""
        regs_assign = ""
        counter = 0

        for idx, item in enumerate(self.model.lists_of_thresholds):
            if len(item) > 0:
                name = self.model.feature_df.at[idx,'Name']
                regs_rst += "\t\t\t\treg_cmp_output.{name} <= (others => '0');\n".format(name=name)
                regs_assign += "\t\t\t\tif CMP_ORD_EN({idx}) = '1' then\n".format(idx=counter)
                regs_assign += "\t\t\t\t\treg_cmp_output.{name} <= CMP_ORD.{name};\n".format(name=name)
                regs_assign += "\t\t\t\tend if;\n"
                counter += 1

        template = TemplateFile(["template", "mem-c_ord", "mem-c_ord_barrier.vhd"])
        dict = {"num_cmps" : counter, "regs_rst" : regs_rst, "regs_assign" : regs_assign}
        template.apply(dict, output_file = os.path.join(self.output_dir, "ord_barrier.vhd"))
    
    # -----------------------------------------------------------------------------
    def generate_top(self, pes):
        template_top = TemplateFile(["template", "mem-c_ord", "mem-c_ord_top.vhd"])
        template_pkg = TemplateFile(["template", "mem-c_ord", "dtype_memc_ord_pkg.vhd"])

        data_type = get_output_datatype(self.model.output_value_quantization)
        
        pe_instances = self.get_pe_instances(pes, data_type)
        cmp_instances, cmp_count = self.get_cmp_instances_group()
        pkg_signals = self.get_pkg_signals()

        dict = {"pkg_signals" : pkg_signals}
        template_pkg.apply(dict, output_file = os.path.join(self.output_dir, "dtype_memc_ord_pkg.vhd"))

        dict = {"pe_instances" : pe_instances, "cmp_instances" : cmp_instances, "num_cmps" : cmp_count,
                "num_pes" : pes, "num_trees" : self.model.num_trees, "num_classes" : self.model.num_classes, "num_iters" : self.model.num_iterations}
        template_top.apply(dict, output_file = os.path.join(self.output_dir, "top.vhd"))

    # -----------------------------------------------------------------------------
    def generate_files(self, pes, iters):
        l_filenames = [] 
        l_filenames.append(os.path.join(self.output_dir, 'dtype_memc_ord_pkg.vhd'))
        l_filenames.append(os.path.join(self.output_dir, 'mux.vhd'))
        l_filenames.append(os.path.join(self.output_dir, 'pes', 'pe_fsm.vhd'))
        l_filenames.append(os.path.join(self.output_dir, 'ord_barrier.vhd'))

        l_filenames.append(os.path.join(self.output_dir, 'comparators', 'cmp_ord_fsm.vhd'))
        for idx, _ in enumerate(self.lists_of_cmp_features):
             l_filenames.append(os.path.join(self.output_dir, 'comparators', 'rom{idx}t.vhd'.format(idx=idx)))
             l_filenames.append(os.path.join(self.output_dir, 'comparators', 'cmp_ord_core{idx}.vhd'.format(idx=idx)))
             l_filenames.append(os.path.join(self.output_dir, 'comparators', 'cmp_ord{idx}.vhd'.format(idx=idx)))

        for idx in range(pes):
            l_filenames.append(os.path.join(self.output_dir, 'pes', 'rom{idx}i.vhd'.format(idx=idx)))
            if iters > 1:
                l_filenames.append(os.path.join(self.output_dir, 'pes', 'rom{idx}s.vhd'.format(idx=idx)))
            l_filenames.append(os.path.join(self.output_dir, 'pes', 'pe{idx}.vhd'.format(idx=idx)))

        l_filenames.append(os.path.join(self.output_dir, 'top.vhd'))

        write_filename_list(self.output_dir, l_filenames)

    # -----------------------------------------------------------------------------
    def get_leaf_size(self):
        
        leaf_size_list = []
        for idx in range(self.model.num_classes):
            _, _, _, _, instr_size, _ = self.generate_mem_content(idx, self.model.num_iterations)
            leaf_size_list.append(instr_size-1)

        print("Min. leaf size:", min(leaf_size_list))
        self.model.get_leaves_values()

    # -----------------------------------------------------------------------------
    def run(self, iters):
        pes = self.model.num_classes
        clean_dir(self.output_dir)
        self.generate_group_bin_search(iters)        
        self.generate_cmp_ord_barrier()
        self.generate_mux()
        self.generate_pes(pes, iters)
        self.generate_top(pes)
        self.generate_files(pes, iters)
        # self.get_leaf_size()

