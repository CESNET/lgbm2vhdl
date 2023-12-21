library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;
use ieee.fixed_float_types.all;
use ieee.fixed_pkg.all;
use ieee.numeric_std.all;
use work.dtype_pkg.all;

entity CMP_ORDER_CORE{idx} is
port(
    CLK         : in std_logic;
    RST         : in std_logic;
    
    START       : in std_logic;
    
    RD          : out std_logic;
    RADDR       : out std_logic_vector({feature_addr_size}-1 downto 0);
    RDATA       : in std_logic_vector({feature_data_size}-1 downto 0);

    WR          : out std_logic;
    WADDR       : out std_logic_vector({feature_addr_size}-1 downto 0);
    WDATA       : out std_logic_vector({stride_size} downto 0);

    FINISH      : out std_logic
);
end CMP_ORDER_CORE{idx};

architecture behavioral of CMP_ORDER_CORE{idx} is
    type t_stride_arr is array (0 to {num_features}-1) of std_logic_vector({stride_size}-1 downto 0);
    signal stride_arr : t_stride_arr := ({stride_content});

    type t_start_arr is array (0 to {num_features}-1) of std_logic_vector({addr_size}-1 downto 0);
    signal start_arr : t_start_arr := ({start_content});

    signal reg_pipe_en0  : std_logic;
    signal reg_pipe_en1  : std_logic;
    signal reg_pipe_en2  : std_logic;

    signal feature       : {data_type};
    signal reg_feature2  : {data_type};
    signal reg_stride0   : std_logic_vector({stride_size}-1 downto 0);
    signal reg_stride1   : std_logic_vector({stride_size}-1 downto 0);
    signal reg_stride2   : std_logic_vector({stride_size}-1 downto 0);
    signal reg_stride_in : std_logic_vector({stride_size}-1 downto 0);
    signal stride        : std_logic_vector({stride_size}-1 downto 0);

    signal rom_en       : std_logic;
    signal rom_addr     : std_logic_vector({addr_size}-1 downto 0);
    signal reg_rom_addr0 : std_logic_vector({addr_size}-1 downto 0);
    signal reg_rom_addr1 : std_logic_vector({addr_size}-1 downto 0);
    signal reg_rom_addr2 : std_logic_vector({addr_size}-1 downto 0);
    signal reg_rom_addr_in : std_logic_vector({addr_size}-1 downto 0);
    signal rom_data     : {data_type};
    signal reg_rom_data2 : {data_type};

    signal right_addr   : std_logic_vector({addr_size}-1 downto 0);
    signal left_addr    : std_logic_vector({addr_size}-1 downto 0);
    signal next_addr    : std_logic_vector({addr_size}-1 downto 0);
    signal addr_diff     : std_logic_vector({addr_size}-1 downto 0);

    signal start_addr        : std_logic_vector({addr_size}-1 downto 0);
    signal reg_start_addr0   : std_logic_vector({addr_size}-1 downto 0);
    signal reg_start_addr1   : std_logic_vector({addr_size}-1 downto 0);
    signal reg_start_addr2   : std_logic_vector({addr_size}-1 downto 0);
    signal reg_start_addr_in : std_logic_vector({addr_size}-1 downto 0);

    signal cnt_feature  : std_logic_vector({feature_addr_size}-1 downto 0);
    signal cnt_feature_en : std_logic;

    signal reg_cnt_feature0 : std_logic_vector({feature_addr_size}-1 downto 0);
    signal reg_cnt_feature1 : std_logic_vector({feature_addr_size}-1 downto 0);
    signal reg_cnt_feature2 : std_logic_vector({feature_addr_size}-1 downto 0);
    signal reg_cnt_feature_in : std_logic_vector({feature_addr_size}-1 downto 0);

    signal reg_order    : std_logic_vector({stride_size} downto 0);
    signal reg_order_en : std_logic;
    signal reg_order_addr : std_logic_vector({feature_addr_size}-1 downto 0);
   
    signal reg_left_only0 : std_logic;
    signal reg_left_only1 : std_logic;
    signal reg_left_only2 : std_logic;
    signal reg_left_only_in : std_logic;

    signal last_iter    : std_logic;
    signal ext_last_iter : std_logic;
    signal last_feature : std_logic;
    signal reg_last_feature : std_logic;

    signal reg_ext_last_iter0 : std_logic;
    signal reg_ext_last_iter1 : std_logic;
    signal reg_ext_last_iter2 : std_logic;

    signal cmp_lt       : std_logic;
    signal cmp_eq       : std_logic;
    signal cmp_gt       : std_logic;

    signal fsm_init1    : std_logic;
    signal fsm_init2    : std_logic;
    signal fsm_work     : std_logic;
    signal fsm_finish   : std_logic;

    signal cnt_mt       : std_logic_vector(1 downto 0);
    signal cnt_mt_over  : std_logic;
    signal reg_active_threads : std_logic_vector(3 downto 0);
    signal all_threads_finished : std_logic;
    signal last_step    : std_logic;

begin
    -- ------------------------------------------------------------------------
    last_iter <= '1' when reg_pipe_en2 = '1' and reg_stride2 = std_logic_vector(to_unsigned(0, reg_stride2'length)) else '0';
    ext_last_iter <= reg_pipe_en2 and last_iter and cmp_lt and reg_left_only2 and not reg_ext_last_iter2;
    last_step <= (last_iter and not ext_last_iter) or (reg_pipe_en2 and cmp_eq) or reg_ext_last_iter2;

    rom_en <= reg_pipe_en0;
    ROM_U : entity work.ROM{idx}t(arch_auto)
    port map(CLK, rom_en, reg_rom_addr0, rom_data);
    
    cnt_feature_en <= (fsm_init2 or last_step) and not last_feature;

    -- Feature counter
    process(CLK)
    begin
        if (rising_edge(CLK)) then
            if RST = '1' or fsm_finish = '1' then
                cnt_feature <= (others => '0');
            else
                if cnt_feature_en = '1' then
                    cnt_feature <= cnt_feature + 1;
                end if;
            end if;
        end if;
    end process;

    reg_cnt_feature_in <= cnt_feature when fsm_init2 = '1' or last_step='1' else reg_cnt_feature2;
    -- Feature counter register
    process(CLK)
    begin
        if (rising_edge(CLK)) then
            if RST = '1' or fsm_finish = '1' then
                reg_cnt_feature0 <= (others => '0');
                reg_cnt_feature1 <= (others => '0');
                reg_cnt_feature2 <= (others => '0');
            else
                reg_cnt_feature0 <= reg_cnt_feature_in;
                reg_cnt_feature1 <= reg_cnt_feature0;
                reg_cnt_feature2 <= reg_cnt_feature1;
            end if;
        end if;
    end process;

    last_feature <= '1' when cnt_feature = std_logic_vector(to_unsigned({num_features}-1, cnt_feature'length)) else '0';

    -- Last feature register
    process(CLK)
    begin
        if (rising_edge(CLK)) then
            if RST = '1' or fsm_finish = '1' then
                reg_last_feature <= '0';
            else
                if fsm_init2 = '1' or last_step = '1' then
                    reg_last_feature <= last_feature;
                end if;
            end if;
        end if;
    end process;

    -- Thread counter
    process(CLK)
    begin
        if (rising_edge(CLK)) then
            if RST = '1' or fsm_finish = '1' or cnt_mt_over = '1' then
                cnt_mt <= (others => '0');
            else
                if fsm_init2 = '1' or fsm_work = '1' then
                    cnt_mt <= cnt_mt + 1;
                end if;
            end if;
        end if;
    end process;

    cnt_mt_over <= '1' when cnt_mt = "10" else '0';

    -- Register Active Threads
    process(CLK)
    begin
        if (rising_edge(CLK)) then
            if RST = '1' or fsm_finish = '1' then
                reg_active_threads <= (others => '0');
            else
                if fsm_init2 = '1' and reg_last_feature = '0' then
                    reg_active_threads(conv_integer(cnt_mt)) <= '1';
                elsif last_step = '1' and reg_last_feature = '1' then
                    reg_active_threads(conv_integer(cnt_mt)) <= '0';
                end if;
            end if;
        end if;
    end process;
    
    all_threads_finished <= '1' when reg_active_threads = "0000" else '0';

    -- Data Registers
    process(CLK)
    begin
        if (rising_edge(CLK)) then
            if RST = '1' or fsm_finish = '1' then
                reg_rom_data2 <= (others => '0');
                reg_feature2 <= (others => '0');

                reg_pipe_en0 <= '0';
                reg_pipe_en1 <= '0';
                reg_pipe_en2 <= '0';

                reg_ext_last_iter0 <= '0';
                reg_ext_last_iter1 <= '0';
                reg_ext_last_iter2 <= '0';
            else
                reg_rom_data2 <= rom_data;
                reg_feature2 <= feature;
                
                reg_pipe_en0 <= (reg_pipe_en2 and not(last_step and reg_last_feature)) or (fsm_init2 and not last_iter);
                reg_pipe_en1 <= reg_pipe_en0;
                reg_pipe_en2 <= reg_pipe_en1;

                reg_ext_last_iter0 <= ext_last_iter;
                reg_ext_last_iter1 <= reg_ext_last_iter0;
                reg_ext_last_iter2 <= reg_ext_last_iter1;
            end if;
        end if;
    end process;

    -- ROM Address Multiplexor
    left_addr <= reg_rom_addr2 - reg_stride2;
    right_addr <= reg_rom_addr2 + reg_stride2;
    next_addr <= right_addr when cmp_gt = '1' else left_addr;
    rom_addr <= reg_start_addr2 when ext_last_iter = '1' else next_addr;

    start_addr <= start_arr(conv_integer(cnt_feature));
    reg_rom_addr_in <= start_addr + stride when fsm_init2 = '1' or last_step = '1' else rom_addr;

    -- Address Register
    process(CLK)
    begin
        if (rising_edge(CLK)) then
            if RST = '1' or fsm_finish = '1' then
                reg_rom_addr0 <= (others => '0');
                reg_rom_addr1 <= (others => '0');
                reg_rom_addr2 <= (others => '0');
            else
                reg_rom_addr0 <= reg_rom_addr_in;
                reg_rom_addr1 <= reg_rom_addr0;
                reg_rom_addr2 <= reg_rom_addr1;
            end if;
        end if;
    end process;

    stride <= stride_arr(conv_integer(cnt_feature));
    reg_stride_in <= stride when fsm_init2 = '1' or last_step = '1' else reg_stride2; 

    -- Stride Register
    process(CLK)
    begin
        if (rising_edge(CLK)) then
            if RST = '1' or fsm_finish = '1' then
                reg_stride0 <= (others => '0');
                reg_stride1 <= (others => '0');
                reg_stride2 <= (others => '0');
            else
                reg_stride0 <= reg_stride_in;
                reg_stride1 <= '0' & reg_stride0(reg_stride0'high downto 1);
                reg_stride2 <= reg_stride1;
            end if;
        end if;
    end process;      

    reg_start_addr_in <= start_addr when fsm_init2 = '1' or last_step = '1' else reg_start_addr2;

    -- Start Addr Register
    process(CLK)
    begin
        if (rising_edge(CLK)) then
            if RST = '1' or fsm_finish = '1' then
                reg_start_addr0 <= (others => '0');
                reg_start_addr1 <= (others => '0');
                reg_start_addr2 <= (others => '0');
            else
                reg_start_addr0 <= reg_start_addr_in;
                reg_start_addr1 <= reg_start_addr0;
                reg_start_addr2 <= reg_start_addr1;
            end if;
        end if;
    end process;      

    reg_left_only_in <= '1' when fsm_init2 = '1' or last_step = '1' else (reg_left_only2 and cmp_lt);

    -- Left Only Register
    process(CLK)
    begin
        if (rising_edge(CLK)) then
            if RST = '1' or fsm_finish = '1' then
                reg_left_only0 <= '0';
                reg_left_only1 <= '0';
                reg_left_only2 <= '0';
            else
                reg_left_only0 <= reg_left_only_in;
                reg_left_only1 <= reg_left_only0;
                reg_left_only2 <= reg_left_only1;
            end if;
        end if;
    end process;      
    
    -- ------------------------------------------------------------------------
    RD <= reg_pipe_en0;
    RADDR <= reg_cnt_feature0;
    feature <= {datatype_conv};

    -- Comparators
    cmp_lt <= '1' when reg_feature2 < reg_rom_data2 else '0';
    cmp_eq <= '1' when reg_feature2 = reg_rom_data2 else '0';
    cmp_gt <= '1' when reg_feature2 > reg_rom_data2 else '0';

    addr_diff <= reg_rom_addr2 - reg_start_addr2;

    -- Output Order Register
    process(CLK)
    begin
        if (rising_edge(CLK)) then
            if RST = '1' then
                reg_order <= (others => '0');
                reg_order_en <= '0';
                reg_order_addr <= (others => '0');
            else
                if last_step = '1' then
                    if cmp_gt = '1' then 
                        reg_order <= addr_diff({stride_size} downto 0) + 1;
                    else
                        reg_order <= addr_diff({stride_size} downto 0);
                    end if;
                end if;
                reg_order_en <= last_step;
                reg_order_addr <= reg_cnt_feature2;
            end if;
        end if;
    end process;

    -- Finite State Machine
    FSM_U : entity work.cmp_ord_fsm(behavioral)
    port map(CLK, RST, START, cnt_mt_over, all_threads_finished, fsm_init1, fsm_init2, fsm_work, fsm_finish);

    WR      <= reg_order_en;
    WADDR   <= reg_order_addr;
    WDATA   <= reg_order;
    FINISH  <= fsm_finish;

end behavioral;
