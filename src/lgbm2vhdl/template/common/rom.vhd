library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;
use ieee.fixed_float_types.all;
use ieee.fixed_pkg.all;
use ieee.numeric_std.all;

entity ROM{idx} is
port(
    CLK : in std_logic;
    EN  : in std_logic;
    ADDR : in std_logic_vector({addr_size}-1 downto 0);
    DATA : out {data_type}
);
end ROM{idx};

architecture arch_block of ROM{idx} is
    type rom_type is array (0 to {items}-1) of {data_type};
    signal ROM : rom_type := ({rom_content});
    attribute ramstyle : string;
    attribute ramstyle of ROM : signal is "M20K";
    attribute rom_style : string;
    attribute rom_style of ROM : signal is "block";

begin
    process(CLK)
    begin
        if rising_edge(CLK) then
            if EN = '1' then
                DATA <= ROM(conv_integer(ADDR));
            end if;
        end if;
    end process;
end arch_block;

architecture arch_dist of ROM{idx} is
    type rom_type is array (0 to {items}-1) of {data_type};
    signal ROM : rom_type := ({rom_content});
    attribute ramstyle : string;
    attribute ramstyle of ROM : signal is "MLAB";
    attribute rom_style : string;
    attribute rom_style of ROM : signal is "distributed";

begin
    process(CLK)
    begin
        if rising_edge(CLK) then
            if EN = '1' then
                DATA <= ROM(conv_integer(ADDR));
            end if;
        end if;
    end process;
end arch_dist;

architecture arch_auto of ROM{idx} is
    type rom_type is array (0 to {items}-1) of {data_type};
    signal ROM : rom_type := ({rom_content});

begin
    process(CLK)
    begin
        if rising_edge(CLK) then
            if EN = '1' then
                DATA <= ROM(conv_integer(ADDR));
            end if;
        end if;
    end process;
end arch_auto;
