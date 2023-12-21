library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;
use ieee.fixed_float_types.all;
use ieee.fixed_pkg.all;
use work.dtype_pkg.all;
use work.dtype_memc_ord_pkg.all;

entity ORD_BARRIER is
port(
    CLK         : in std_logic;
    RST         : in std_logic;

    CMP_ORD     : in t_cmp_ord;
    CMP_ORD_EN  : in std_logic_vector({num_cmps}-1 downto 0);

    OUTPUT      : out t_cmp_ord;
    OUTPUT_EN   : out std_logic
);
end ORD_BARRIER;

architecture behavioral of ORD_BARRIER is
    signal reg_cmp_output       : t_cmp_ord;
    signal reg_finished         : std_logic_vector({num_cmps}-1 downto 0);
    signal reg_finished_clean   : std_logic;
    signal cmp_output_en        : std_logic;
    signal reg_output_en        : std_logic;

begin

    -- Data registers
    process(CLK)
    begin
        if (rising_edge(CLK)) then
            if RST = '1' then
{regs_rst}
            else
{regs_assign}
            end if;
        end if;
    end process;

    reg_finished_clean  <= RST or cmp_output_en;

    -- Finished flags register
    process(CLK)
    begin
        if (rising_edge(CLK)) then
            if reg_finished_clean = '1' then
                reg_finished <= (others => '0');
            else
                for i in 0 to {num_cmps}-1 loop
                    if CMP_ORD_EN(i) = '1' then
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
    OUTPUT <= reg_cmp_output;

end behavioral;