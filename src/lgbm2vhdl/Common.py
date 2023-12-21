import math
import os
import shutil
import numpy as np
from fxpmath import Fxp
from importlib.resources import files

from .TemplateFile import TemplateFile

# -----------------------------------------------------------------------------
def clean_dir(dir, excluded_files=[]):

    # Create output directory if not exists        
    if not os.path.exists(dir):
        os.makedirs(dir)

    # Clean output directory
    for filename in os.listdir(dir):
        file_path = os.path.join(dir, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                if filename not in excluded_files:
                    os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))

# -----------------------------------------------------------------------------
def get_output_datatype(output_value_quantization):

    (int_flag, signed_flag, int_size, dec_size) = output_value_quantization

    if int_flag:
        data_type = '{signed}fixed({higher} downto -{lower})'.format(signed=signed_flag, higher=int_size-1, lower=dec_size)
    else:
        signed_str = 's'if signed_flag else 'u'
        data_type = '{signed}fixed({higher} downto -{lower})'.format(signed=signed_str, higher=int_size-1, lower=dec_size)

    return data_type

# -----------------------------------------------------------------------------
def get_threshold_index(model, feature, threshold):
    list_of_thresholds = model.lists_of_thresholds[feature]
    int_flag = model.feature_df.at[feature,'Int']

    if int_flag:
        search_threshold = int(math.floor(threshold))  
    else: 
        search_threshold = threshold
    
    return np.where(list_of_thresholds == search_threshold)[0][0]

# -----------------------------------------------------------------------------
def get_features_ports(model):
    features_ports = ""

    for idx in range(len(model.feature_df.index)):
        name = model.feature_df.at[idx,'Name']
        int_flag = model.feature_df.at[idx,'Int']
        signed_flag = model.feature_df.at[idx,'Signed']
        int_size = model.feature_df.at[idx,'IntSize']
        dec_size = model.feature_df.at[idx,'DecSize']

        if int_flag:
            signed_str = ''if signed_flag else 'un'
            features_ports += '\t\t{name}:\t{signed_str}signed({higher} downto {lower});\n'.format(name=name, signed_str=signed_str, higher=int_size+dec_size-1, lower=0)
        else:
            signed_flag = 's'if signed_flag else 'u'
            features_ports += '\t\t{name}:\t{signed}fixed({higher} downto -{lower});\n'.format(name=name, signed=signed_flag, higher=int_size-1, lower=dec_size)

    return features_ports

# -----------------------------------------------------------------------------
def write_filename_list(output_dir, l_filename):
    output_file = os.path.join(output_dir, 'files.txt')
    
    with open(output_file, 'w') as fw:
        fw.write('\n'.join(l_filename))

# -----------------------------------------------------------------------------
def get_max_feature_size(model):
    
    max_size = 0

    for idx in range(model.num_features):
        int_size = model.feature_df.at[idx,'IntSize']
        dec_size = model.feature_df.at[idx,'DecSize']
        size = int_size + dec_size
        if size > max_size:
            max_size = size

    return max_size

# -----------------------------------------------------------------------------
def get_mem_attrib(technology, req_type):
    if technology == 'Intel':
        mem_attr = "ramstyle"
        if req_type == 'block':
            mem_type = "M20K , no_rw_check"
        if req_type == 'distributed':
            mem_type = "MLAB , no_rw_check"
        if req_type == 'auto':
            mem_type = "no_rw_check"
    else:
        mem_attr = "ram_style"
        if req_type == 'block':
            mem_type = "block"
        if req_type == 'distributed':
            mem_type = "distributed"
        if req_type == 'auto':
            mem_type = "auto"
    
    return mem_attr, mem_type

# -----------------------------------------------------------------------------
def generate_all_files(source_dir, output_dir):

    # List of all source filesnames
    output_file = os.path.join(output_dir, 'files.txt')
    filenames = []
    filenames.append(os.path.join(source_dir, 'common', 'files.txt'))
    filenames.append(os.path.join(source_dir, 'lgbm', 'files.txt'))
    filenames.append(os.path.join(source_dir, 'wrapper', 'files.txt'))

    # Merge all files.txt files
    with open(output_file,'w') as outfile:
        fname_content = []
        for fname in filenames:
            with open(fname) as infile:
                fname_content.append(infile.read())
        outfile.write('\n'.join(fname_content))

# -----------------------------------------------------------------------------
def generate_build_files(source_dir, technology, period):

    output_dir = os.path.join(source_dir, 'build', technology)
    clean_dir(output_dir)

    # Generate list of all files
    generate_all_files(source_dir, output_dir)

    # Prepare build files for selected technology
    if technology == "Intel":
        shutil.copyfile(files('lgbm2vhdl').joinpath("template", "build", "Makefile.intel"), os.path.join(output_dir, "Makefile"))
        shutil.copyfile(files('lgbm2vhdl').joinpath("template", "build", "design.intel.tcl"), os.path.join(output_dir, "design.tcl"))

        template = TemplateFile(["template", "build", "design.sdc"])
        dict = {"period" : period}
        template.apply(dict, os.path.join(output_dir, "design.sdc"))

    if technology == "AMD":
        shutil.copyfile(files('lgbm2vhdl').joinpath("template", "build", "Makefile.amd"), os.path.join(output_dir, "Makefile"))
        shutil.copyfile(files('lgbm2vhdl').joinpath("template", "build", "design.amd.tcl"), os.path.join(output_dir, "design.tcl"))

        template = TemplateFile(["template", "build", "design.xdc"])
        dict = {"period" : period}
        template.apply(dict, os.path.join(output_dir, "design.xdc"))

# -----------------------------------------------------------------------------
