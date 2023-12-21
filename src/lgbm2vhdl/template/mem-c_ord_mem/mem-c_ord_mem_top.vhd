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
    type t_pe_raddr is array (0 to {num_classes}-1) of std_logic_vector({pe_addr_size}-1 downto 0);
    type t_pe_rdata is array (0 to {num_classes}-1) of std_logic_vector({pe_data_size}-1 downto 0);
    type t_dist_info is array (0 to {num_features}-1) of std_logic_vector({dist_info_size}-1 downto 0);
    signal dist_info            : t_dist_info := ({dist_info_content});

    signal dist_wr              : std_logic_vector({num_cmps}+1-1 downto 0);
    signal dist_waddr           : std_logic_vector({max_feature_addr_size}-1 downto 0);
    signal dist_wdata           : std_logic_vector({mi_data_size}-1 downto 0);
    signal dist_info_rec        : std_logic_vector({dist_info_size}-1 downto 0);
    signal dist_cmp             : std_logic_vector({dist_info_size}-{max_feature_addr_size}-1 downto 0);

    signal cnt_feature          : std_logic_vector({mi_addr_size}-1 downto 0);
    signal reg_cnt_feature      : std_logic_vector({mi_addr_size}-1 downto 0);
    signal reg_wr               : std_logic;
    signal cnt_feature_init     : std_logic;
    signal cnt_feature_en       : std_logic;
    signal cnt_feature_overflow : std_logic;

    signal fsm_cnt_feature_en   : std_logic;
    signal fsm_cnt_feature_init : std_logic;
    signal fsm_feature_finish   : std_logic;

    signal cmp_rd               : std_logic_vector({num_cmps}-1 downto 0);
    signal cmp_wr               : std_logic_vector({num_cmps}-1 downto 0);
    signal cmp_finish           : std_logic_vector({num_cmps}-1 downto 0);
{cmp_signals}
    signal pe_input_en          : std_logic;

    signal pe_rd                : std_logic_vector({num_classes}-1 downto 0);
    signal pe_raddr             : t_pe_raddr;
    signal pe_rdata             : t_pe_rdata;

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
    dist_wdata <= MI_RDATA;
    dist_info_rec <= dist_info(conv_integer(reg_cnt_feature));
    dist_waddr <= dist_info_rec({max_feature_addr_size}-1 downto 0);

    dist_cmp <= dist_info_rec({dist_info_size}-1 downto {max_feature_addr_size});

    process(dist_cmp, reg_wr)
    begin
        dist_wr <= (others => '0'); -- default
        dist_wr(conv_integer(dist_cmp)) <= reg_wr;
    end process;

{cmp_mem_instances}
{cmp_instances}
{pe_mem_instances}
    BARRIER_FEATURES_U: entity work.barrier(behavioral)
    generic map({num_cmps})
    port map(CLK, RST, cmp_finish, pe_input_en);

{pe_instances}
    BARRIER_CLASS_U: entity work.barrier(behavioral)
    generic map({num_classes})
    port map(CLK, RST, pe_output_en, OUTPUT_EN);

end behavioral;