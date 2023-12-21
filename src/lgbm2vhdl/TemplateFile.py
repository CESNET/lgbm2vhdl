from importlib.resources import files

class TemplateFile:
    
    def __init__(self, path_list):
        self.path_list = path_list

    def apply(self, dict, output_file):
        data = files('lgbm2vhdl').joinpath(*self.path_list).read_text()
        data_param = data.format(**dict)

        with open(output_file, 'w') as fw:
            fw.write(data_param)