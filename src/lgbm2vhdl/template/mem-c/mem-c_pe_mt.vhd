library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;
use ieee.fixed_float_types.all;
use ieee.fixed_pkg.all;
use ieee.numeric_std.all;
use work.dtype_pkg.all;
{package}

entity PE{idx} is
port(
    CLK         : in std_logic;
    RST         : in std_logic;

    INPUTS_EN   : in std_logic;
    INPUTS      : in {input_data_type};
    OUTPUT_EN   : out std_logic;
    OUTPUT      : out {output_data_type}
);
end PE{idx};

architecture behavioral of PE{idx} is
    constant C_INSTR_SIZE  : integer := 1 + {signed_mux} + {group_size} + {item_size} + {muxout_size} + {instr_addr_inc_size};
    constant C_ITERS       : integer := {iters};
    constant C_SIGNED_MUX  : integer := {signed_mux};

    signal sel_item     : std_logic_vector({group_size}+{item_size}-1 downto 0);
    signal threshold    : std_logic_vector({muxout_size}-1 downto 0);
    signal r_next_addr  : std_logic_vector({instr_addr_size}-1 downto 0);
    signal l_next_addr  : std_logic_vector({instr_addr_size}-1 downto 0);
    signal next_addr    : std_logic_vector({instr_addr_size}-1 downto 0);
    signal r_next_addr_inc : std_logic_vector({instr_addr_inc_size}-1 downto 0);

    signal instr_rom_en   : std_logic;
    signal instr_rom_addr : std_logic_vector({instr_addr_size}-1 downto 0);
    signal instr_rom_data : std_logic_vector(C_INSTR_SIZE-1 downto 0);
    signal reg_instr_rom_data2 : std_logic_vector(C_INSTR_SIZE-1 downto 0);
    signal reg_instr_rom_data3 : std_logic_vector(C_INSTR_SIZE-1 downto 0);
    signal reg_instr_rom_addr0: std_logic_vector({instr_addr_size}-1 downto 0);
    signal reg_instr_rom_addr1: std_logic_vector({instr_addr_size}-1 downto 0);
    signal reg_instr_rom_addr2: std_logic_vector({instr_addr_size}-1 downto 0);
    signal reg_instr_rom_addr3: std_logic_vector({instr_addr_size}-1 downto 0);

    signal start_rom_en   : std_logic;
    signal start_rom_addr : std_logic_vector({start_addr_size} downto 0);
    signal start_rom_data : std_logic_vector({instr_addr_size}-1 downto 0);

    signal mux_output   : std_logic_vector({muxout_size}-1 downto 0);
    signal reg_mux_output3 : std_logic_vector({muxout_size}-1 downto 0);
    signal fsm_init1    : std_logic;
    signal fsm_init2    : std_logic;
    signal fsm_work     : std_logic;
    signal fsm_finish   : std_logic;
    signal leaf_node    : std_logic;
    signal leaf_node_prefetch : std_logic;
    signal last_iter    : std_logic;
    signal reg_last_iter    : std_logic;
    signal cmp_out      : std_logic;
    signal leaf_value   : {output_data_type};

    signal signed_flag   : std_logic;
    signal mux_cmp       : std_logic_vector({muxout_size} downto 0);
    signal threshold_cmp : std_logic_vector({muxout_size} downto 0);
    signal mux_extension : std_logic;
    signal threshold_extension : std_logic;

    signal reg_pipe_en0  : std_logic;
    signal reg_pipe_en1  : std_logic;
    signal reg_pipe_en2  : std_logic;
    signal reg_pipe_en3  : std_logic;

    signal cnt_mt        : std_logic_vector(1 downto 0);
    signal cnt_mt_over   : std_logic;
    signal reg_active_threads : std_logic_vector(3 downto 0);
    signal all_threads_finished : std_logic;

    signal reg_class     : {output_data_type};
    signal reg_class_en  : std_logic;

begin

    -- ------------------------------------------------------------------------
    -- Start Address Memory

    GEN_START_U: if C_ITERS = 1  generate
        start_rom_data <= (others=>'0');

        process(CLK)
        begin
            if (rising_edge(CLK)) then
                if RST = '1' or fsm_finish = '1' then
                    reg_last_iter <= '0';
                else
                    if fsm_init2 = '1' then
                        reg_last_iter <= '1';
                    end if;
                end if;
            end if;
        end process;

    else generate
        start_rom_en <= (fsm_init1 or leaf_node_prefetch) and not last_iter;
        {srom_inst}

        -- Address counter
        process(CLK)
        begin
            if (rising_edge(CLK)) then
                if RST = '1' or fsm_finish = '1' then
                    start_rom_addr <= (others => '0');
                else
                    if start_rom_en = '1' then
                        start_rom_addr <= start_rom_addr + 1;
                    end if;
                end if;
            end if;
        end process;

        last_iter <= '1' when start_rom_addr = std_logic_vector(to_unsigned({iters}, start_rom_addr'length)) else '0';

        process(CLK)
        begin
            if (rising_edge(CLK)) then
                if RST = '1' then
                    reg_last_iter <= '0';
                else
                    reg_last_iter <= last_iter;
                end if;
            end if;
        end process;

    end generate GEN_START_U;
    -- ------------------------------------------------------------------------
    -- Instruction Memory

    instr_rom_en <= reg_pipe_en0;
    ROMi_U : entity work.ROM{idx}i(arch_block)
    port map(CLK, instr_rom_en, reg_instr_rom_addr0, instr_rom_data);

    leaf_node_prefetch <= reg_pipe_en2 and reg_instr_rom_data2(1+{signed_mux}+{group_size}+{item_size}+{muxout_size}+{instr_addr_inc_size}-1);
    leaf_node <= reg_pipe_en3 and reg_instr_rom_data3(1+{signed_mux}+{group_size}+{item_size}+{muxout_size}+{instr_addr_inc_size}-1);
    signed_flag <= reg_instr_rom_data3({signed_mux}+{group_size}+{item_size}+{muxout_size}+{instr_addr_inc_size}-1);
    sel_item <= reg_instr_rom_data2({group_size}+{item_size}+{muxout_size}+{instr_addr_inc_size}-1 downto {muxout_size}+{instr_addr_inc_size});
    threshold <= reg_instr_rom_data3({muxout_size}+{instr_addr_inc_size}-1 downto {instr_addr_inc_size});
    r_next_addr_inc <= reg_instr_rom_data3({instr_addr_inc_size}-1 downto 0);
    leaf_value <= to_sfixed(reg_instr_rom_data3({dtype_size}-1 downto 0), {dtype_left}-1, -{dtype_right});   -- FIXME: conversion to sfixed (other data types possible)
    
    
    instr_rom_addr <= start_rom_data when fsm_init2 = '1' or (leaf_node = '1' and reg_last_iter = '0') else next_addr;

    -- Pipeline Registers
    process(CLK)
    begin
        if (rising_edge(CLK)) then
            if RST = '1' then
                reg_pipe_en0         <= '0';
                reg_pipe_en1         <= '0';
                reg_pipe_en2         <= '0';
                reg_pipe_en3         <= '0';

                reg_instr_rom_addr0  <= (others => '0');
                reg_instr_rom_addr1  <= (others => '0');
                reg_instr_rom_addr2  <= (others => '0');
                reg_instr_rom_addr3  <= (others => '0');

                reg_instr_rom_data2  <= (others => '0');
                reg_instr_rom_data3  <= (others => '0');

                reg_mux_output3      <= (others => '0');
            else
                reg_pipe_en0         <= (reg_pipe_en3 and not(leaf_node and reg_last_iter)) or (fsm_init2 and not reg_last_iter);
                reg_pipe_en1         <= reg_pipe_en0;
                reg_pipe_en2         <= reg_pipe_en1;
                reg_pipe_en3         <= reg_pipe_en2;

                reg_instr_rom_addr0  <= instr_rom_addr;
                reg_instr_rom_addr1  <= reg_instr_rom_addr0;
                reg_instr_rom_addr2  <= reg_instr_rom_addr1;
                reg_instr_rom_addr3  <= reg_instr_rom_addr2;
                
                reg_instr_rom_data2  <= instr_rom_data;
                reg_instr_rom_data3  <= reg_instr_rom_data2;
                
                reg_mux_output3      <= mux_output;
            end if;
        end if;
    end process;

    -- Thread counter
    process(CLK)
    begin
        if (rising_edge(CLK)) then
            if RST = '1' or fsm_finish = '1' then
                cnt_mt <= (others => '0');
            else
                if fsm_init2 = '1' or fsm_work = '1' then
                    cnt_mt <= cnt_mt + 1;
                end if;
            end if;
        end if;
    end process;

    cnt_mt_over <= '1' when cnt_mt = "11" else '0';

    -- Register Active Threads
    process(CLK)
    begin
        if (rising_edge(CLK)) then
            if RST = '1' or fsm_finish = '1' then
                reg_active_threads <= (others => '0');
            else
                if fsm_init2 = '1' and reg_last_iter = '0' then
                    reg_active_threads(conv_integer(cnt_mt)) <= '1';
                elsif leaf_node = '1' and reg_last_iter = '1' then
                    reg_active_threads(conv_integer(cnt_mt)) <= '0';
                end if;
            end if;
        end if;
    end process;
    
    all_threads_finished <= '1' when reg_active_threads = "0000" else '0';

    -- ------------------------------------------------------------------------
    -- PE Internal Logic

    -- Feature Multiplexer
    MUX_U : entity work.mux(behavioral)
    port map(INPUTS, sel_item, mux_output);

GEN_SIGNED_MUX_U: if C_SIGNED_MUX = 1  generate
    -- signed bit extension before comparison
    mux_extension <= reg_mux_output3({muxout_size}-1) when signed_flag = '1' else '0';
    threshold_extension <= threshold({muxout_size}-1) when signed_flag = '1' else '0';
    mux_cmp <= mux_extension & reg_mux_output3;
    threshold_cmp <= threshold_extension & threshold;

    -- Comparator
    cmp_out <= '0' when signed(mux_cmp) <= signed(threshold_cmp) else '1';
else generate
    cmp_out <= '0' when unsigned(reg_mux_output3) <= unsigned(threshold) else '1';
end generate GEN_SIGNED_MUX_U;


    -- Addr Multiplexer
    l_next_addr <= reg_instr_rom_addr3 + 1;
    r_next_addr <= reg_instr_rom_addr3 + r_next_addr_inc;

    next_addr <= r_next_addr when cmp_out = '1' else l_next_addr;

    -- ------------------------------------------------------------------------
    -- Finite State Machine

    FSM_U : entity work.pe_fsm(behavioral)
    port map(CLK, RST, INPUTS_EN, cnt_mt_over, all_threads_finished, fsm_init1, fsm_init2, fsm_work, fsm_finish);

    process(CLK)
    begin
        if (rising_edge(CLK)) then
            if INPUTS_EN = '1' then
                reg_class <= (others => '0');
                reg_class_en <= '0';
            else
                if leaf_node = '1' then
                    reg_class <= resize(reg_class + leaf_value, {dtype_left}-1, -{dtype_right}, round_style => fixed_truncate, overflow_style => fixed_wrap);
                end if;
                reg_class_en <= fsm_finish;
            end if;
        end if;
    end process;
    
    OUTPUT <= reg_class;
    OUTPUT_EN <= reg_class_en;

end behavioral;
