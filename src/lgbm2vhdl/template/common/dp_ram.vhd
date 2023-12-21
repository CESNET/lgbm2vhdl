library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;

entity DP_RAM is
generic(
    ADDR_WIDTH : integer;
    DATA_WIDTH : integer;
    ITEMS      : integer
);
port(
    CLK         : in std_logic;

    WR          : in std_logic;
    WADDR       : in std_logic_vector(ADDR_WIDTH-1 downto 0);
    WDATA       : in std_logic_vector(DATA_WIDTH-1 downto 0);

    RD          : in std_logic;
    RADDR       : in std_logic_vector(ADDR_WIDTH-1 downto 0);
    RDATA       : out std_logic_vector(DATA_WIDTH-1 downto 0)
);
end DP_RAM;

architecture arch_block of DP_RAM is
    type ram_type is array (ITEMS-1 downto 0) of std_logic_vector(DATA_WIDTH-1 downto 0);
    signal RAM : ram_type;
    attribute ramstyle : string;
    attribute ramstyle of RAM : signal is "M20K , no_rw_check";
    attribute ram_style : string;
    attribute ram_style of RAM : signal is "block";

begin
    process(CLK)
    begin
        if rising_edge(CLK) then
            if WR = '1' then
                RAM(conv_integer(WADDR)) <= WDATA;
            end if;
            if RD = '1' then
                RDATA <= RAM(conv_integer(RADDR));
            end if;
        end if;
    end process;
  
end arch_block;

architecture arch_dist of DP_RAM is
    type ram_type is array (ITEMS-1 downto 0) of std_logic_vector(DATA_WIDTH-1 downto 0);
    signal RAM : ram_type;
    attribute ramstyle : string;
    attribute ramstyle of RAM : signal is "MLAB , no_rw_check";
    attribute ram_style : string;
    attribute ram_style of RAM : signal is "distributed";

begin
    process(CLK)
    begin
        if rising_edge(CLK) then
            if WR = '1' then
                RAM(conv_integer(WADDR)) <= WDATA;
            end if;
            if RD = '1' then
                RDATA <= RAM(conv_integer(RADDR));
            end if;
        end if;
    end process;
  
end arch_dist;

architecture arch_auto of DP_RAM is
    type ram_type is array (ITEMS-1 downto 0) of std_logic_vector(DATA_WIDTH-1 downto 0);
    signal RAM : ram_type;
    attribute ramstyle : string;
    attribute ramstyle of RAM : signal is "no_rw_check";
    attribute ram_style : string;
    attribute ram_style of RAM : signal is "auto";

begin
    process(CLK)
    begin
        if rising_edge(CLK) then
            if WR = '1' then
                RAM(conv_integer(WADDR)) <= WDATA;
            end if;
            if RD = '1' then
                RDATA <= RAM(conv_integer(RADDR));
            end if;
        end if;
    end process;
  
end arch_auto;