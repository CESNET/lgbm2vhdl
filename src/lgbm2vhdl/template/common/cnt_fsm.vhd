library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;

entity CNT_FSM is
port(
    CLK         : in std_logic;
    RST         : in std_logic;

    START       : in std_logic;
    CNT_OVER    : in std_logic;
    
    CNT_INIT    : out std_logic;
    CNT_EN      : out std_logic;
    FINISH      : out std_logic
);
end CNT_FSM;

architecture behavioral of CNT_FSM is
    type state_available is (S_INIT,S_RUN);
    signal present_state, next_state: state_available;

begin

    process (CLK)
    begin
        if rising_edge(CLK)  then
            if (RST='1') then
                present_state <= S_INIT;
            else
                present_state <= next_state;
            end if;
        end if;
    end process;

    process (present_state, START, CNT_OVER)
    begin
        CNT_INIT <= '0';
        CNT_EN   <= '0';
        FINISH   <= '0';

        case present_state is
        when S_INIT =>
            next_state <= S_INIT;
            if(START ='1') then
                next_state <= S_RUN;
                CNT_INIT <= '1';
            end if;  
        when S_RUN =>
            next_state <= S_RUN;
            CNT_EN <= '1';
            if(CNT_OVER ='1') then
                next_state <= S_INIT;
                FINISH   <= '1';
            end if;
        when others =>
            next_state <= S_INIT;    
        end case;
    end process;

end behavioral;
