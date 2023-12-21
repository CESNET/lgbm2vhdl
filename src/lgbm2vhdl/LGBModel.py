import math
import lightgbm as lgb
import pandas as pd
import numpy as np

from .LGBTree import LGBTree

class LGBModel:

    # -----------------------------------------------------------------------------
    def __init__(self, model_filename, feature_quantizaton):
        self.filename = model_filename
        self.lgb_model = lgb.Booster(model_file=model_filename)
        self.model = self.lgb_model.dump_model()
        self.num_features = self.model['max_feature_idx'] + 1
        self.num_classes = self.model['num_class']
        self.feature_df = pd.read_csv(feature_quantizaton, sep=';')
        self.output_value_quantization = tuple(self.feature_df.iloc[self.num_features])[1:]
        print('Number of features:', self.num_features)
        print('Number of classes:', self.num_classes)

        self.tree_list = self.model['tree_info']
        self.num_trees = len(self.tree_list)
        print('Number of trees:', self.num_trees)
        # print(self.feature_df)
        self.num_iterations = int(self.num_trees/self.num_classes)
        print('Number of iterations:', self.num_iterations)

    # -----------------------------------------------------------------------------
    def get_tree(self, idx):
        return LGBTree(self.tree_list[idx])

    # -----------------------------------------------------------------------------
    def print_info(self):
        print('--------------- Model info ---------------------')
        print(self.model.keys())
        print('name', self.model['name'])
        print('version', self.model['version'])
        print('num_class', self.model['num_class'])
        print('num_tree_per_iteration', self.model['num_tree_per_iteration'])
        print('label_index', self.model['label_index'])
        print('max_feature_idx', self.model['max_feature_idx'])
        print('objective', self.model['objective'])
        print('average_output', self.model['average_output'])
        print('feature_names', self.model['feature_names'])
        print('monotone_constraints', self.model['monotone_constraints'])
        print('feature_infos', self.model['feature_infos'])
        # print('tree_info', self.model['tree_info'])
        print('feature_importances', self.model['feature_importances'])
        print('pandas_categorical', self.model['pandas_categorical'])


    # -----------------------------------------------------------------------------
    def print_stat(self, l, name):
    
        lsum = sum(l)
        lmin = min(l)
        lmax = max(l)
        lavg = lsum/len(l)

        print("{:<20} : {:6d} {:5d} {:5d} {:8.1f}".format(name, lsum, lmin, lmax, lavg))


    # -----------------------------------------------------------------------------
    def get_params(self):

        list_num_splits = []
        list_num_leaves = []
        list_num_nodes = []
        list_depth = []

        for idx in range(self.num_trees):
            tree = self.get_tree(idx)
            depth, splits, leaves, _ = tree.get_params()

            list_depth.append(depth)
            list_num_splits.append(splits)
            list_num_leaves.append(leaves)
            list_num_nodes.append(splits+leaves)

        self.list_depth = list_depth
        self.list_num_splits = list_num_splits
        self.list_num_leaves = list_num_leaves
        self.list_num_nodes = list_num_nodes

        self.print_stat(list_depth, "Tree depth")
        self.print_stat(list_num_splits, "Number of splits")
        self.print_stat(list_num_leaves, "Number of leaves")
        self.print_stat(list_num_nodes, "Number of nodes")

    # -----------------------------------------------------------------------------
    def get_leaves_values(self):

        list_leaves_values = []

        for tree in self.tree_list:
            stack = [(tree['tree_structure'], 0)]  

            while len(stack) > 0:
                node, depth = stack.pop()
                is_split_node = 'split_index' in node.keys()

                if is_split_node:
                    stack.append((node['left_child'], depth + 1))
                    stack.append((node['right_child'], depth + 1))
                else:
                    list_leaves_values.append(node['leaf_value'])

        print("Leaves values (min, max, avg):", min(list_leaves_values), max(list_leaves_values), sum(list_leaves_values)/len(list_leaves_values))
        
        return list_leaves_values

    # -----------------------------------------------------------------------------
    def get_tree_thresholds(self, tree):
        lists_of_thresholds = [[] for _ in range(self.num_features)]
        stack = [(tree['tree_structure'], 0)]
        
        while len(stack) > 0:
            node, depth = stack.pop()
            is_split_node = 'split_index' in node.keys()

            if is_split_node:
                feature = node['split_feature']
                threshold = node['threshold']
                decision_type = node['decision_type']
                if decision_type != '<=':
                     raise Exception('ERROR: Unsupported decision type: {}'.format(decision_type))
                lists_of_thresholds[feature].append(threshold)
                stack.append((node['left_child'], depth + 1))
                stack.append((node['right_child'], depth + 1))

        return lists_of_thresholds

    # -----------------------------------------------------------------------------
    def get_uniq_model_thresholds(self, int_check=True):
        lists_of_thresholds = [[] for _ in range(self.num_features)]
        lists_of_us_thresholds = [[] for _ in range(self.num_features)]

        tree_list = self.model['tree_info']

        for tree in tree_list:
            thresholds = self.get_tree_thresholds(tree)
            for i, t in enumerate(thresholds):
                lists_of_thresholds[i].extend(t)

        # Get unique thresholds
        sum_orig = 0
        sum_uniq = 0
        sum_uniq_int = 0
        for i, l in enumerate(lists_of_thresholds):
            orig_len = len(l)
            if int_check:
                # Get integer threshold for integers features
                feature_int = self.feature_df.at[i, "Int"]
                if feature_int:
                    for j, elem in enumerate(l):
                        l[j] = int(math.floor(elem))
            l_uniq = np.unique(l)
            uniq_len = len(l_uniq)
            # print(orig_len, uniq_len)
            lists_of_us_thresholds[i] = l_uniq
            sum_orig += orig_len
            sum_uniq += uniq_len

        # print(lists_of_us_thresholds[1])
        print("Thresholds sums, uniq:", sum_orig, sum_uniq)
        self.lists_of_thresholds = lists_of_us_thresholds

    # -----------------------------------------------------------------------------
    def get_time_bin_search(self):
        
        st_list = []
        for idx, item in enumerate(self.lists_of_thresholds):
            if len(item) > 0:
                search_time = int(math.ceil(math.log2(len(item))))
                # print("Feature",  idx, len(item), search_time)
                st_list.append(search_time)

        print("Sum of binary search times: ", sum(st_list))

    # -----------------------------------------------------------------------------
    def get_time_iter_processing(self, iterations):
        
        max_list = []
        min_list = []
        avg_list = []
        for cls_idx in range(self.num_classes):
            
            max_depth = 0
            min_depth = 0
            avg_depth = 0
            for iter in range(iterations):
                tree = self.get_tree(cls_idx + iter*self.num_classes)
                _, _, _, depth_list = tree.get_params()

                max_depth += max(depth_list)
                min_depth += min(depth_list)
                avg_depth += int(sum(depth_list)/len(depth_list))
            
                # print ("\t", iter, min_depth, avg_depth, max_depth)

            max_list.append(max_depth)
            min_list.append(min_depth)
            avg_list.append(avg_depth)
            
            # print(cls_idx, min_depth, avg_depth, max_depth)

        print("Time for iteration processing (min, avg, max): ", max(min_list), int(sum(avg_list)/len(avg_list)), max(max_list))

    # -----------------------------------------------------------------------------
    def plot_tree(self, tree_idx):
        # ax = lgb.plot_tree(self.lgb_model, tree_index=tree_idx)
        res = lgb.create_tree_digraph(self.lgb_model, tree_index=tree_idx)
        res.render(format='png').replace('\\', '/')

    # -----------------------------------------------------------------------------
    def generate_mem_content(self, tree_idx, iters):

        # -----------------------------------------------------------------
        # get memory items info            
        node_addr = 0
        max_diff_addr = 0
        mem_arr = []
        start_addr_list = [node_addr]

        for iter in range(iters):
            tree = self.get_tree(tree_idx + iter*self.num_classes)        
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

        return mem_arr, start_addr_list, max_diff_addr
    
    # -----------------------------------------------------------------------------
    def simulate_tree(self, tree_idx, iters, test_vec):
        mem_arr, start_arr, _ = self.generate_mem_content(tree_idx, iters)

        mem_addr_arr_iter = []
        for iter in range(iters):
            mem_addr_arr = []
            mem_addr = start_arr[iter]
            leaf = False
            while not leaf:
                node = mem_arr[mem_addr]
                mem_addr_arr.append(mem_addr)
                if node['type'] == 'NODE':
                    if test_vec[node['feature']] <= node['threshold']:
                        mem_addr += 1
                    else:
                        mem_addr += node['next_addr']
                else:
                    leaf = True
            
            mem_addr_arr_iter.append(mem_addr_arr)

        return mem_addr_arr_iter

    # -----------------------------------------------------------------------------
    def get_order_arr(self, test_vec):
        self.get_uniq_model_thresholds()

        order_arr = []
        for idx, t_list in enumerate(self.lists_of_thresholds):
            order_pos = 0
            feature = test_vec[idx]
            
            if len(t_list) > 0:
                for threshold in t_list:
                    if feature > threshold:
                        order_pos += 1
                    else:
                        continue 

                order_arr.append(order_pos)

        return order_arr