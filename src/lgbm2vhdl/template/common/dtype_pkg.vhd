library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.fixed_float_types.all;
use ieee.fixed_pkg.all;

package dtype_pkg is
    type t_class_array is array ({num_classes}-1 downto 0) of {data_type};
    type t_class_inputs is array ({num_iters}-1 downto 0) of {data_type};

    type t_features is record
{features}
    end record t_features;
end package;