library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;
use ieee.fixed_float_types.all;
use ieee.fixed_pkg.all;
use ieee.numeric_std.all;
use work.dtype_pkg.all;
{package}

entity MUX is
port(
    INPUTS      : in {datatype};

    SEL_ITEM    : in std_logic_vector({g_size}+{i_size}-1 downto 0);

    OUTPUT      : out std_logic_vector({m_size}-1 downto 0)
);
end MUX;

architecture behavioral of MUX is

{output_signals}	
begin

{item_mux_inst}	

{group_mux_inst}	

end behavioral;
