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
begin
{mem_instances}
end behavioral;