library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;
use ieee.fixed_float_types.all;
use ieee.fixed_pkg.all;
use work.dtype_pkg.all;
use ieee.numeric_std.all;

entity WRAPPER is
port(
    CLK : in std_logic;
    RST : in std_logic;

    START       : in std_logic;
    FINISH      : out std_logic;

    MI_IN_WR    : in std_logic;
    MI_IN_WADDR  : in std_logic_vector({mi_in_addr_size}-1 downto 0);
    MI_IN_WDATA  : in std_logic_vector({mi_in_data_size}-1 downto 0);

    MI_OUT_RADDR : in std_logic_vector({mi_out_addr_size}-1 downto 0);
    MI_OUT_RDATA : out std_logic_vector({mi_out_data_size}-1 downto 0)
);
end WRAPPER;

architecture behavioral of WRAPPER is
    signal mi_in_rd         : std_logic;
    signal mi_in_raddr      : std_logic_vector({mi_in_addr_size}-1 downto 0);
    signal mi_in_rdata      : std_logic_vector({mi_in_data_size}-1 downto 0);
    signal mi_out_rd        : std_logic;
    signal mi_out_wr        : std_logic;
    signal mi_out_wdata     : std_logic_vector({mi_out_data_size}-1 downto 0);

    signal cnt_class        : std_logic_vector({mi_out_addr_size}-1 downto 0);
    signal cnt_class_init   : std_logic;
    signal cnt_class_en     : std_logic;
    signal cnt_class_overflow : std_logic;

    signal class_en         : std_logic;

    signal class            : t_class_array;
    signal reg_class        : t_class_array;

    signal fsm_cnt_feature_en   : std_logic;
    signal fsm_cnt_feature_init : std_logic;
    signal fsm_feature_finish   : std_logic;
    signal fsm_cnt_class_en     : std_logic;
    signal fsm_cnt_class_init   : std_logic;
    signal fsm_class_finish     : std_logic;

begin

    mi_in_rd <= '1';
    MI_IN_U: entity work.dp_ram(arch_auto)
    generic map({mi_in_addr_size}, {mi_in_data_size}, {num_features})
    port map(CLK, MI_IN_WR, MI_IN_WADDR, MI_IN_WDATA, mi_in_rd, mi_in_raddr, mi_in_rdata);
 

    LGBT_U: entity work.top_tree_mem(behavioral)
    port map(CLK, RST, START, mi_in_raddr, mi_in_rdata, class, class_en);

    -- registers for output classes
    process(CLK)
    begin
        if (rising_edge(CLK)) then
            if RST = '1' then
                for i in 0 to {num_classes}-1 loop
                    reg_class(i) <= (others => '0');
                end loop;
            else
                for i in 0 to {num_classes}-1 loop
                    if class_en = '1' then
                        reg_class(i) <= class(i);
                    end if;
                end loop;
            end if;
        end if;
    end process;

    cnt_class_overflow <= '1' when cnt_class = std_logic_vector(to_unsigned({num_classes}-1, {mi_out_addr_size})) else '0';
    cnt_class_init <= RST or cnt_class_overflow or fsm_cnt_class_init;
    cnt_class_en <= fsm_cnt_class_en;

    -- classes counter
    process(CLK)
    begin
        if (rising_edge(CLK)) then
            if cnt_class_init = '1' then
                cnt_class <= (others => '0');
            else
                if cnt_class_en = '1' then
                    cnt_class <= cnt_class + 1;
                end if;
            end if;
        end if;
    end process;

    FSM_CLASS_U: entity work.cnt_fsm(behavioral)
    port map(CLK, RST, class_en, cnt_class_overflow, fsm_cnt_class_init, fsm_cnt_class_en, FINISH);

    -- generic multiplexor of classes
    mi_out_wdata <= to_slv(reg_class(to_integer(unsigned(cnt_class))));
    mi_out_wr <= fsm_cnt_class_en;

    mi_out_rd <= '1';
    MI_OUT_U: entity work.dp_ram(arch_auto)
    generic map({mi_out_addr_size}, {mi_out_data_size}, {num_classes})
    port map(CLK, mi_out_wr, cnt_class, mi_out_wdata, mi_out_rd, MI_OUT_RADDR, MI_OUT_RDATA);

end behavioral;
