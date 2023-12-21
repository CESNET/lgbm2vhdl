library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;

entity BARRIER is
generic(
    ITEMS      : integer
);
port(
    CLK         : in std_logic;
    RST         : in std_logic;

    INPUT_EN    : in std_logic_vector(ITEMS-1 downto 0);
    OUTPUT_EN   : out std_logic
);
end BARRIER;

architecture behavioral of BARRIER is
    signal reg_finished         : std_logic_vector(ITEMS-1 downto 0);
    signal reg_finished_clean   : std_logic;
    signal cmp_output_en        : std_logic;
    signal reg_output_en        : std_logic;

begin

    reg_finished_clean  <= RST or cmp_output_en;

    -- Finished flags register
    process(CLK)
    begin
        if (rising_edge(CLK)) then
            if reg_finished_clean = '1' then
                reg_finished <= (others => '0');
            else
                for i in 0 to ITEMS-1 loop
                    if INPUT_EN(i) = '1' then
                        reg_finished(i) <= '1';
                    end if;
                end loop;
            end if;
        end if;
    end process;

    -- Comparator - all units finished?
    cmp_output_en <= '1' when reg_finished = (reg_finished'range => '1') else '0';

    -- Output Enable register
    process(CLK)
    begin
        if (rising_edge(CLK)) then
            if RST = '1' then
                reg_output_en <= '0';
            else
                reg_output_en <= cmp_output_en;
            end if;
        end if;
    end process;

    OUTPUT_EN <= reg_output_en;

end behavioral;