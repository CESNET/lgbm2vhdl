library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;
use ieee.fixed_float_types.all;
use ieee.fixed_pkg.all;
use work.dtype_pkg.all;

entity TOP_TREE is
port(
    CLK         : in std_logic;
    RST         : in std_logic;

    FEATURES    : in t_features;
    FEATURES_EN : in std_logic;

    CLASS       : out t_class_array;
    OUTPUT_EN   : out std_logic
);
end TOP_TREE;

architecture behavioral of TOP_TREE is
    signal pe_output_en         : std_logic_vector({num_classes}-1 downto 0);

begin

{pe_instances}
    BARRIER_U: entity work.barrier(behavioral)
    generic map({num_classes})
    port map(CLK, RST, pe_output_en, OUTPUT_EN);

end behavioral;