library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;
use ieee.fixed_float_types.all;
use ieee.fixed_pkg.all;
use work.dtype_pkg.all;
use work.dtype_memc_ord_pkg.all;

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

    signal cmp_output           : t_cmp_ord;
    signal cmp_output_en        : std_logic_vector({num_cmps}-1 downto 0);
    signal pe_input             : t_cmp_ord;
    signal pe_input_en          : std_logic;
   
    signal pe_output_en         : std_logic_vector({num_classes}-1 downto 0);

begin

{cmp_instances}
    ORD_BARRIER_U: entity work.ord_barrier(behavioral)
    port map(CLK, RST, cmp_output, cmp_output_en, pe_input, pe_input_en);

{pe_instances}
    BARRIER_CLASS_U: entity work.barrier(behavioral)
    generic map({num_classes})
    port map(CLK, RST, pe_output_en, OUTPUT_EN);

end behavioral;