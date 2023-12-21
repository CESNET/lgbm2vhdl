class LGBTree:

    # -----------------------------------------------------------------------------
    def __init__(self, tree):
        self.tree_dict = tree
        self.max_depth, self.nodes, self.leaves, _ = self.get_params()

    # -----------------------------------------------------------------------------
    def print_info(self):
        print('--------------- Tree info ---------------------')
        print(self.tree_dict.keys())
        print(self.tree_dict['tree_index'])
        print(self.tree_dict['num_leaves'])
        print(self.tree_dict['num_cat'])
        print(self.tree_dict['shrinkage'])
        # print(self.tree['tree_structure'])

    # -----------------------------------------------------------------------------
    def get_params(self):
        stack = [(self.tree_dict['tree_structure'], 0)]  
        max_depth = 0
        nodes = 0
        leaves = 0
        leaves_depth = []

        while len(stack) > 0:
            node, depth = stack.pop()
            if depth > max_depth:
                max_depth = depth

            is_split_node = 'split_index' in node.keys()

            if is_split_node:
                nodes += 1
                stack.append((node['left_child'], depth + 1))
                stack.append((node['right_child'], depth + 1))
            else:
                leaves += 1
                leaves_depth.append(depth)

        return max_depth+1, nodes, leaves, leaves_depth
    