# lgbm2vhdl

This project aims to create a tool for automated conversion of the LightGBM library model to the digital circuit description in VHDL. The input to this conversion is an arbitrary model obtained by the LightGBM library. The output is a VHDL code that can be synthesized and loaded, for example, on configurable chips with FPGA technology.

Simulations for the ModelSIM environment are also prepared to test the resulting VHDL code. Within these simulations, a testbench file including additional supporting scripts for the ModelSIM environment is created, and it is automatically verified that for a given input test vector, the VHDL architecture gives the same prediction results as the original LightGBM model executed in Python.

## Installation

Install the package from pip with:

```bash
pip install lgbm2vhdl
```

## Usage Example

```py
import os
from lgbm2vhdl.LGBM2VHDL import LGBM2VHDL

# Example model and quantization definition
model_filename = os.path.join("data", "example_model_class3.txt")
quantization_filename = os.path.join("data", "example_model_class3-quantization.csv")

# Model loading
lvg = LGBM2VHDL(model_filename, quantization_filename, working_dir="./tmp")

# Generation of VHDL files
lvg.generate_vhdl(architecture="mem-c")

# Running simulation
lvg.run_simulation(architecture="mem-c")

```
### Definition of quantization

Some of the input features may be in the form of decimal numbers, usually in floating-point format (exponent and mantissa). Processing this type of number is very computationally resource intensive in FPGA chips, and therefore, these numbers need to be converted to a fixed-point format where a specific number of bits is always specified for the integer and decimal parts of the number. For each such feature, it is necessary to specify the parameters for floating to fixed point conversion. This type of conversion must be performed not only for the input features, but also for the model output values representing the degree of membership (called log-odds ratio) of the input object to the selected class. Therefore, an important input of the conversion is also a CSV file with a definition for quantizing the input features and the output values of the model. 

#### Format of quantization CSV file

For each input feature it is necessary to enter one line in the CSV file containing information about the number format that will be used at the circuit implementation level. In addition, the CSV file will contain one more line defining the number format for the model output values (log-odds ratio). Thus, in total, the file must contain a number of lines corresponding to the number of features + 1.

The format of each line is identical and consists of 5 items:
1. Name of the feature
2. Integer/Decimal number (*True* if a number is integer)
3. Signed/Unsigned number (*True* if a number is signed)
4. Number of bits for integer part of a number
5. Number of bits for decimal part of a number (zero in case of integer numbers)


### Architecture specification

The *lgbm2vhdl* module supports up to four different types of resulting VHDL circuit architectures.
1. **mem-c** - It represents the standard Memory Centric architecture for implementing decision trees and Gradient Boosting models [[1]](#1)).
2. **mem-c_ord** - Similar to **mem-c**, but the values of the input features and the thresholds (within instructions) are replaced by the rank order within the sorted sequence of all thresholds used in the model.
3. **mem-c_mem** - Similar to **mem-c**, but process element multiplexers are replaced by a memory block into which the input features are sequentially loaded.
4. **mem-c_ord_mem** - It combines both the **mem-c_ord** and **mem-c_ord_mem** optimizations described above.

### Acknowledgements

    This project was supported by the Ministry of the Interior of the Czech Republic, grant No. VJ02010024: Flow-Based Encrypted Traffic Analysis.

## References 
<a id="1">[1]</a> Alcolea, A.; Resano, J. FPGA Accelerator for Gradient Boosting Decision Trees. Electronics 2021, 10, 314. https://doi.org/10.3390/electronics10030314.
