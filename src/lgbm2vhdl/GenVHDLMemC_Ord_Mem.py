import math
import os
import shutil
from fxpmath import Fxp
from importlib.resources import files

from .TemplateFile import TemplateFile
from .Common import clean_dir, get_output_datatype, write_filename_list, get_threshold_index, get_mem_attrib, get_max_feature_size

class GenVHDLMemC_Ord_Mem:
    
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
        list_of_datatypes = []
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
                list_of_datatypes.append(key)

        # print(dict_mapping)
        # print(lists_of_cmp_features)

        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # Create common data structure

        cmp_group_info_list = []
        max_order_size_list = []
        feature_addr_size_list = []
        for datatype, feature_list in zip(list_of_datatypes, lists_of_cmp_features):
            num_features = len(feature_list) 
            feature_addr_size = int(math.ceil(math.log2(num_features)))
            feature_data_size = datatype[2] + datatype[3]
            
            # Get max number of features thresholds
            order_size_list = []
            for fid in feature_list:
                list_of_thresholds = self.model.lists_of_thresholds[fid]
                thresholds = len(list_of_thresholds)
                if thresholds == 1:
                    thresholds = 2
                order_size_list.append(int(math.ceil(math.log2(thresholds)))+1)
            
            max_order_size = max(order_size_list)
            max_order_size_list.append(max_order_size)
            feature_addr_size_list.append(feature_addr_size)

            cmp_group_info = {'feature_list' : feature_list, 'datatype' : datatype, 'num_features' : num_features,  
                            'feature_addr_size' : feature_addr_size, 'feature_data_size' : feature_data_size,
                            'max_order_size' : max_order_size}
            cmp_group_info_list.append(cmp_group_info)

        max_feature_addr_size = max(feature_addr_size_list)
        pe_addr_size = max_feature_addr_size + int(math.ceil(math.log2(len(lists_of_cmp_features))))
        self.cmp_group_info_list = cmp_group_info_list
        self.cmps_group_info = {'max_order_size' : max(max_order_size_list), 'max_feature_addr_size' : max_feature_addr_size, 'pe_addr_size' : pe_addr_size}
        
        print(self.cmp_group_info_list)
        print(self.cmps_group_info)

        self.i_size = self.cmps_group_info['max_feature_addr_size']
        self.m_size = self.cmps_group_info['max_order_size']
        self.g_size = self.cmps_group_info['pe_addr_size'] - self.cmps_group_info['max_feature_addr_size']

    # -----------------------------------------------------------------------------
    def generate_group_bin_search(self, iters):
        self.model.get_uniq_model_thresholds()

        # Create output directory if not exists        
        output_dir_comparators = os.path.join(self.output_dir, "comparators")
        if not os.path.exists(output_dir_comparators):
            os.makedirs(output_dir_comparators)

        self.get_groups_of_features()

        template_rom = TemplateFile(["template", "common", "rom.vhd"])

        for c_idx, cmp_group_info in enumerate(self.cmp_group_info_list):
            print("Feature Comparator Group", c_idx)       
            
            max_addr_size = 0
            rom_inst = ""
            stride_list = []

            mem_content_list = []
            start_addr_list = []
            final_items_list = []
            start_addr = 0
            final_items = 0

            cmp_data_type = cmp_group_info['datatype']

            int_flag = cmp_data_type[0]
            signed_flag = cmp_data_type[1]
            int_size = cmp_data_type[2]
            dec_size = cmp_data_type[3]
            # print(int_flag, signed_flag, int_size, dec_size)

            if int_flag:
                signed_str = ''if signed_flag else 'un'
                data_type = "{signed_str}signed({higher} downto {lower})".format(signed_str=signed_str, higher=int_size+dec_size-1, lower=0)
                datatype_conv = "{signed_str}signed(RDATA)".format(signed_str=signed_str)
            else:
                signed_str = 's'if signed_flag else 'u'
                data_type = "{signed_str}fixed({higher} downto -{lower})".format(signed_str=signed_str, higher=int_size-1, lower=dec_size)
                datatype_conv = "to_{signed_str}fixed(RDATA, {high_idx}, {low_idx})".format(signed_str=signed_str, high_idx=int_size-1, low_idx=-dec_size)

            for f_idx, f_id in enumerate(cmp_group_info['feature_list']):
                start_addr += final_items
                start_addr_list.append(start_addr)

                list_of_thresholds = self.model.lists_of_thresholds[f_id]
                # print(f_id, list_of_thresholds)

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

            num_features = len(cmp_group_info['feature_list'])
            stride_content_str = ", ".join(stride_content)
            start_content_str = ", ".join(start_content)
            output_file = os.path.join(output_dir_comparators, "cmp_ord{idx}.vhd".format(idx=c_idx))
            template_cmp = TemplateFile(["template", "cmp_ord", "cmp_ord_group_mt_core.vhd"])
            dict = {"idx" : str(c_idx), "addr_size" : mem_addr_size, "stride_size" : max_addr_size, "data_type" : data_type, "rom_inst" : rom_inst,
                    "num_features" : num_features, "feature_addr_size" : cmp_group_info['feature_addr_size'], "feature_data_size" : cmp_group_info['feature_data_size'],
                    "stride_content" : stride_content_str,  "start_content" : start_content_str, 'datatype_conv' : datatype_conv}
            template_cmp.apply(dict, output_file)

        shutil.copyfile(files('lgbm2vhdl').joinpath("template", "cmp_ord", "cmp_ord_fsm_group_mt.vhd"), os.path.join(output_dir_comparators, "cmp_ord_fsm.vhd"))

    # -----------------------------------------------------------------------------
    def get_item_group_idx(self, feature):

        for group_idx, cmp_group_info in enumerate(self.cmp_group_info_list):
            for item_idx, val in enumerate(cmp_group_info['feature_list']):
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
    def generate_mem_pe(self):
        cmp_interface = ""
        mem_instances = ""
        mem_rdata_assign = ""
        mem_rdata_signals = ""

        for idx, cmp_group_info in enumerate(self.cmp_group_info_list):
            cmp_interface += "\tCMP{idx}_WR    : in std_logic;\n".format(idx=idx)
            cmp_interface += "\tCMP{idx}_WADDR : in std_logic_vector({addr_size}-1 downto 0);\n".format(idx=idx, addr_size=cmp_group_info['feature_addr_size'])
            cmp_interface += "\tCMP{idx}_WDATA : in std_logic_vector({data_size}-1 downto 0);\n".format(idx=idx, data_size=cmp_group_info['max_order_size'])
            
            mem_instances += "\tMEM_CMP{idx}_U : entity work.dp_ram(arch_dist)\n".format(idx=idx)
            mem_instances += "\tgeneric map({addr_size}, {data_size}, {items})\n".format(addr_size=cmp_group_info['feature_addr_size'], data_size=cmp_group_info['max_order_size'], items=cmp_group_info['num_features'])

            if len(self.cmp_group_info_list) > 1:
                mem_instances += "\tport map(CLK, CMP{idx}_WR, CMP{idx}_WADDR, CMP{idx}_WDATA, mem_rd({idx}), PE_RADDR({addr_size}-1 downto 0), mem_rdata{idx});\n\n".format(idx=idx, addr_size=cmp_group_info['feature_addr_size'])
            else:
                mem_instances += "\tport map(CLK, CMP{idx}_WR, CMP{idx}_WADDR, CMP{idx}_WDATA, PE_RD, PE_RADDR, PE_RDATA);\n\n".format(idx=idx)

            mem_rdata_assign += "\tmem_rdata({idx}) <= std_logic_vector(resize(unsigned(mem_rdata{idx}), {max_data_size}));\n".format(idx=idx, max_data_size=self.cmps_group_info['max_order_size'])
            mem_rdata_signals += "\tsignal mem_rdata{idx} : std_logic_vector({data_size}-1 downto 0);\n".format(idx=idx, data_size=cmp_group_info['max_order_size'])
        
        if len(self.cmp_group_info_list) > 1:
            template = TemplateFile(["template", "mem-c_ord_mem", "mem-c_ord_mem_mem_pe.vhd"])
        else:
            template = TemplateFile(["template", "mem-c_ord_mem", "mem-c_ord_mem_mem_pe_single.vhd"])

        max_num_cmps = int(pow(2.0, int(math.ceil(math.log2(len(self.cmp_group_info_list))))))
        num_cmps = len(self.cmp_group_info_list)
        dict = {'mem_instances' : mem_instances, 'cmp_interface' : cmp_interface, 'max_num_cmps' : max_num_cmps,
                'max_data_size' : self.cmps_group_info['max_order_size'], 'max_feature_addr_size' : self.cmps_group_info['max_feature_addr_size'], 'pe_addr_size' : self.cmps_group_info['pe_addr_size'],
                'mem_rdata_assign' : mem_rdata_assign, 'mem_rdata_signals' : mem_rdata_signals}
        output_file = os.path.join(self.output_dir, "mem_pe.vhd")
        template.apply(dict, output_file)

    # -----------------------------------------------------------------------------
    def generate_pes(self, pes, iters):

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

            feature_addr_size = self.cmps_group_info['pe_addr_size']
            feature_data_size = self.cmps_group_info['max_order_size']

            dtype_size = int_size + dec_size            
            dict = {"idx" : idx, "instr_addr_size" : instr_addr_size, "instr_addr_inc_size" : instr_addr_inc_size, "start_addr_size" : start_addr_size, "group_size" : self.g_size, "item_size" : self.i_size, "muxout_size" : self.m_size, 
                    "output_data_type" : output_data_type, "dtype_size" : dtype_size, "dtype_left" : self.model.output_value_quantization[2], "dtype_right" : self.model.output_value_quantization[3], "iters" : iters, "srom_inst" : srom_inst, "signed_mux" : 0,
                    "input_data_type" : input_data_type, "feature_addr_size" : feature_addr_size, "feature_data_size" : feature_data_size}

            output_file = os.path.join(output_dir_pes, "pe{idx}.vhd".format(idx=idx))
            template_pes.apply(dict, output_file)

    # -----------------------------------------------------------------------------
    def get_cmp_instances_group(self):

        cmp_instances = ""
        cmp_signals = ""

        for idx, item in enumerate(self.cmp_group_info_list):
            cmp_instances += "\tCMP_ORDER{idx}_U : entity work.CMP_ORDER_CORE{idx}(behavioral)\n".format(idx=idx)
            cmp_instances += "\tport map(CLK, RST, fsm_feature_finish, cmp_rd({idx}), cmp_raddr{idx}, cmp_rdata{idx}, cmp_wr({idx}), cmp_waddr{idx}, cmp_wdata{idx}, cmp_finish({idx}));\n\n".format(idx=idx)
            cmp_signals += "\tsignal cmp_raddr{idx}           : std_logic_vector({size}-1 downto 0);\n".format(idx=idx, size=item['feature_addr_size'])
            cmp_signals += "\tsignal cmp_rdata{idx}           : std_logic_vector({size}-1 downto 0);\n".format(idx=idx, size=item['feature_data_size'])
            cmp_signals += "\tsignal cmp_waddr{idx}           : std_logic_vector({size}-1 downto 0);\n".format(idx=idx, size=item['feature_addr_size'])
            cmp_signals += "\tsignal cmp_wdata{idx}           : std_logic_vector({size}-1 downto 0);\n".format(idx=idx, size=item['max_order_size'])

        cmp_count = len(self.cmp_group_info_list)
        
        return cmp_instances, cmp_count, cmp_signals

    # -----------------------------------------------------------------------------
    def get_mem_instances(self):

        cmp_instances = ""
        pe_instances = ""

        for idx, cmp_group_info in enumerate(self.cmp_group_info_list):
            cmp_instances += "\tMEM_CMP{idx}_U : entity work.dp_ram(arch_dist)\n".format(idx=idx)
            cmp_instances += "\tgeneric map({addr_size}, {data_size}, {items})\n".format(addr_size=cmp_group_info['feature_addr_size'], data_size=cmp_group_info['feature_data_size'], items=cmp_group_info['num_features'])
            cmp_instances += "\tport map(CLK, dist_wr({idx}+1), dist_waddr({addr_size}-1 downto 0), dist_wdata({data_size}-1 downto 0), cmp_rd({idx}), cmp_raddr{idx}, cmp_rdata{idx});\n\n".format(idx=idx, addr_size=cmp_group_info['feature_addr_size'], data_size=cmp_group_info['feature_data_size'])

        cmp_signals = []
        for idx, cmp_group_info in enumerate(self.cmp_group_info_list):
            cmp_signals.append("cmp_wr({idx})".format(idx=idx))
            cmp_signals.append("cmp_waddr{idx}".format(idx=idx))
            cmp_signals.append("cmp_wdata{idx}".format(idx=idx))
        cmp_signals_str = ", ".join(cmp_signals)

        for idx in range(self.model.num_classes):               
            pe_instances += "\tMEM_PE{idx}_U : entity work.mem_pe(behavioral)\n".format(idx=idx)
            pe_instances += "\tport map(CLK, RST, {cmp_signals}, pe_rd({idx}), pe_raddr({idx}), pe_rdata({idx}));\n\n".format(idx=idx, cmp_signals=cmp_signals_str)

        return cmp_instances, pe_instances

    # -----------------------------------------------------------------------------
    def get_pe_instances(self, trees, data_type):

        pe_instances = ""

        for idx in range(trees):
            pe_instances += "\tPE{idx}_U : entity work.PE{idx}(behavioral)\n".format(idx=idx)
            pe_instances += "\tport map(CLK, RST, pe_input_en, pe_rd({idx}), pe_raddr({idx}), pe_rdata({idx}), pe_output_en({idx}), CLASS({idx}));\n\n".format(idx=idx)

        return pe_instances

    # -----------------------------------------------------------------------------
    def get_dist_info_content(self):
        
        
        f_size = self.cmps_group_info['max_feature_addr_size']
        c_size = int(math.ceil(math.log2(len(self.cmp_group_info_list) + 1)))
        init = Fxp(0, False, c_size+f_size, 0)
        dist_info_arr = ["\"" + init.bin() + "\""] * self.model.num_features

        for c_idx, cmp_group_info in enumerate(self.cmp_group_info_list):
            c = Fxp(c_idx+1, False, c_size, 0)
            for f_idx, f_id in enumerate(cmp_group_info['feature_list']):
                f = Fxp(f_idx, False, f_size, 0)
                dist_info_arr[f_id] = "\"" + c.bin() + f.bin() + "\""

        dist_info_content = ", ".join(dist_info_arr)

        return dist_info_content

    # -----------------------------------------------------------------------------
    def generate_top(self, pes):
        template_top = TemplateFile(["template", "mem-c_ord_mem", "mem-c_ord_mem_top.vhd"])

        data_type = get_output_datatype(self.model.output_value_quantization)
        pe_instances = self.get_pe_instances(pes, data_type)
        cmp_mem_instances, pe_mem_instances = self.get_mem_instances()
        cmp_instances, cmp_count, cmp_signals = self.get_cmp_instances_group()

        dist_info_content = self.get_dist_info_content()

        mi_addr_size = int(math.ceil(math.log2(self.model.num_features)))
        mi_data_size = get_max_feature_size(self.model)
        pe_addr_size = self.cmps_group_info['pe_addr_size']
        pe_data_size = self.cmps_group_info['max_order_size']
        dist_info_size = self.cmps_group_info['max_feature_addr_size'] + int(math.ceil(math.log2(cmp_count + 1)))       

        dict = {"pe_instances" : pe_instances, "cmp_instances" : cmp_instances, "num_cmps" : cmp_count, "cmp_mem_instances" : cmp_mem_instances, "pe_mem_instances" : pe_mem_instances,
                "num_pes" : pes, "num_trees" : self.model.num_trees, "num_classes" : self.model.num_classes, "num_iters" : self.model.num_iterations,
                "mi_addr_size" : mi_addr_size, "mi_data_size" : mi_data_size, "pe_addr_size" : pe_addr_size, "pe_data_size" : pe_data_size, "cmp_signals" : cmp_signals, "num_features" : self.model.num_features,
                'max_feature_addr_size' : self.cmps_group_info['max_feature_addr_size'], 'dist_info_size' : dist_info_size, 'dist_info_content' : dist_info_content}
        template_top.apply(dict, output_file = os.path.join(self.output_dir, "top.vhd"))

    # -----------------------------------------------------------------------------
    def generate_files(self, pes, iters):
        l_filenames = [] 
        l_filenames.append(os.path.join(self.output_dir, 'mem_pe.vhd'))
        l_filenames.append(os.path.join(self.output_dir,'pes', 'pe_fsm.vhd'))

        l_filenames.append(os.path.join(self.output_dir, 'comparators', 'cmp_ord_fsm.vhd'))
        for idx, _ in enumerate(self.cmp_group_info_list):
             l_filenames.append(os.path.join(self.output_dir, 'comparators', 'rom{idx}t.vhd'.format(idx=idx)))
             l_filenames.append(os.path.join(self.output_dir, 'comparators', 'cmp_ord{idx}.vhd'.format(idx=idx)))

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
        self.generate_group_bin_search(iters)        
        self.generate_mem_pe()
        self.generate_pes(pes, iters)
        self.generate_top(pes)
        self.generate_files(pes, iters)

