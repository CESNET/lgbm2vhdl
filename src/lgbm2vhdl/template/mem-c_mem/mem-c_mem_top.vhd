library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;
use ieee.fixed_float_types.all;
use ieee.fixed_pkg.all;
use work.dtype_pkg.all;
use ieee.numeric_std.all;

entity TOP_TREE_MEM is
port(
    CLK         : in std_logic;
    RST         : in std_logic;

    START       : in std_logic;

    MI_RADDR    : out std_logic_vector({mi_addr_size}-1 downto 0);
    MI_RDATA    : in std_logic_vector({mi_data_size}-1 downto 0);

    CLASS       : out t_class_array;
    OUTPUT_EN   : out std_logic
);
end TOP_TREE_MEM;

architecture behavioral of TOP_TREE_MEM is
    type t_mi_addr_array is array (0 to {num_classes}-1) of std_logic_vector({mi_addr_size}-1 downto 0);
    type t_mi_data_array is array (0 to {num_classes}-1) of std_logic_vector({mi_data_size}-1 downto 0);

    signal mi_wr                : std_logic;
    signal mi_waddr             : std_logic_vector({mi_addr_size}-1 downto 0);
    signal mi_wdata             : std_logic_vector({mi_data_size}-1 downto 0);
    signal mi_pe_rd             : std_logic_vector({num_classes}-1 downto 0);
    signal mi_pe_raddr          : t_mi_addr_array;
    signal mi_pe_rdata          : t_mi_data_array;

    signal cnt_feature          : std_logic_vector({mi_addr_size}-1 downto 0);
    signal reg_cnt_feature      : std_logic_vector({mi_addr_size}-1 downto 0);
    signal reg_wr               : std_logic;
    signal cnt_feature_init     : std_logic;
    signal cnt_feature_en       : std_logic;
    signal cnt_feature_overflow : std_logic;

    signal fsm_cnt_feature_en   : std_logic;
    signal fsm_cnt_feature_init : std_logic;
    signal fsm_feature_finish   : std_logic;

    signal pe_output_en         : std_logic_vector({num_classes}-1 downto 0);

begin
    cnt_feature_overflow <= '1' when cnt_feature = std_logic_vector(to_unsigned({num_features}-1, {mi_addr_size})) else '0';
    cnt_feature_init <= RST or cnt_feature_overflow or fsm_cnt_feature_init;
    cnt_feature_en <= fsm_cnt_feature_en;

    -- features counter
    process(CLK)
    begin
        if (rising_edge(CLK)) then
            if cnt_feature_init = '1' then
                cnt_feature <= (others => '0');
            else
                if cnt_feature_en = '1' then
                    cnt_feature <= cnt_feature + 1;
                end if;
            end if;
        end if;
    end process;

    FSM_U: entity work.cnt_fsm(behavioral)
    port map(CLK, RST, START, cnt_feature_overflow, fsm_cnt_feature_init, fsm_cnt_feature_en, fsm_feature_finish);

    -- registers
    process(CLK)
    begin
        if (rising_edge(CLK)) then
            if RST = '1' then
                reg_cnt_feature <= (others => '0');
                reg_wr <= '0';
            else
                reg_cnt_feature <= cnt_feature;
                reg_wr <= fsm_cnt_feature_en;
            end if;
        end if;
    end process;

    MI_RADDR <= cnt_feature;
    mi_wr <= reg_wr;
    mi_waddr <= reg_cnt_feature;
    mi_wdata <= MI_RDATA;

LOOP_MEM : for i in 0 to {num_classes}-1 generate
    MEM_U : entity work.dp_ram(arch_auto)
    generic map({mi_addr_size}, {mi_data_size}, {num_features})
    port map(CLK, mi_wr, mi_waddr, mi_wdata, mi_pe_rd(i), mi_pe_raddr(i), mi_pe_rdata(i));
end generate;

{pe_instances}
    BARRIER_U: entity work.barrier(behavioral)
    generic map({num_classes})
    port map(CLK, RST, pe_output_en, OUTPUT_EN);

end behavioral;