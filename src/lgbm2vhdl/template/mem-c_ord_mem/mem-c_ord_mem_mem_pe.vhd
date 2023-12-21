library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;
use ieee.numeric_std.all;

entity MEM_PE is
port(
    CLK         : in std_logic;
    RST         : in std_logic;

{cmp_interface}
    PE_RD       : in std_logic;
    PE_RADDR    : in std_logic_vector({pe_addr_size}-1 downto 0);
    PE_RDATA    : out std_logic_vector({max_data_size}-1 downto 0)
);
end MEM_PE;

architecture behavioral of MEM_PE is
    type t_mem_rdata_arr is array (0 to {max_num_cmps}-1) of std_logic_vector({max_data_size}-1 downto 0);
    signal mem_rdata    : t_mem_rdata_arr := (others=>(others=>'0'));
    signal mem_rd       : std_logic_vector({max_num_cmps}-1 downto 0);
    signal sel          : std_logic_vector({pe_addr_size}-{max_feature_addr_size}-1 downto 0);
    signal reg_sel      : std_logic_vector({pe_addr_size}-{max_feature_addr_size}-1 downto 0);

{mem_rdata_signals}
begin
{mem_instances}
    sel <= PE_RADDR({pe_addr_size}-1 downto {max_feature_addr_size});

    -- generic decoder for rd signal
    process(sel)
	begin
		mem_rd <= (others => '0'); -- default
		mem_rd(to_integer(unsigned(sel))) <= PE_RD;
	end process;

    -- Output Enable register
    process(CLK)
    begin
        if (rising_edge(CLK)) then
            if RST = '1' then
                reg_sel <= (others => '0');
            else
                reg_sel <= sel;
            end if;
        end if;
    end process;

{mem_rdata_assign}
    PE_RDATA <= mem_rdata(conv_integer(reg_sel));

end behavioral;