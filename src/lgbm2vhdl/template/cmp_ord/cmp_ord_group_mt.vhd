library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;
use ieee.fixed_float_types.all;
use ieee.fixed_pkg.all;
use ieee.numeric_std.all;
use work.dtype_pkg.all;

entity CMP_ORDER{idx} is
port(
    CLK         : in std_logic;
    RST         : in std_logic;

    START       : in std_logic;
    {interface}
);
end CMP_ORDER{idx};

architecture behavioral of CMP_ORDER{idx} is

    type t_feature_arr is array (0 to {num_features}-1) of {data_type};
    signal feature_arr  : t_feature_arr;

    signal mux_feature  : {data_type};
    signal reg_mux_feature  : std_logic_vector({feature_data_size}-1 downto 0);
    signal feature_en  : std_logic_vector({num_features}-1 downto 0);

    signal rd          : std_logic;
    signal raddr       : std_logic_vector({feature_addr_size}-1 downto 0);
    signal rdata       : std_logic_vector({feature_data_size}-1 downto 0);
    signal wr          : std_logic;
    signal waddr       : std_logic_vector({feature_addr_size}-1 downto 0);
    signal wdata       : std_logic_vector({stride_size} downto 0);
    signal finish      : std_logic;

begin
    -- ------------------------------------------------------------------------
    {feature_arr_inst}
    mux_feature <= feature_arr(conv_integer(raddr));

    -- Feature Register
    process(CLK)
    begin
        if (rising_edge(CLK)) then
            if RST = '1' then
                reg_mux_feature <= (others => '0');
            else
                reg_mux_feature <= std_logic_vector(mux_feature);               
            end if;
        end if;
    end process;
    
    rdata <= reg_mux_feature;

    -- Multi-thread core
    CORE_U : entity work.cmp_order_core{idx}(behavioral)
    port map(CLK, RST, START, rd, raddr, rdata, wr, waddr, wdata, finish);

    LOOP_FEATURE_EN : for i in 0 to {num_features}-1 generate
        feature_en(i) <= wr when waddr = std_logic_vector(to_unsigned(i, waddr'length)) else '0';
    end generate;

    {output_assign}

end behavioral;
