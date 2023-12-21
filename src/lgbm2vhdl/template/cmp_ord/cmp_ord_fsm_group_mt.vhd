library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;

entity CMP_ORD_FSM is
port(
    CLK         : in std_logic;
    RST         : in std_logic;

    INPUT_EN    : in std_logic;
    CNT_MT_OVER : in std_logic;
    ALL_THREADS_FINISHED : in std_logic;
    
    INIT1       : out std_logic;
    INIT2       : out std_logic;
    WORK        : out std_logic;
    FINISH      : out std_logic
);
end CMP_ORD_FSM;

architecture behavioral of CMP_ORD_FSM is
    type state_available is (S_IDLE, S_ITER_INIT, S_RUN);
    signal present_state, next_state: state_available;

begin

    process (CLK)
    begin
        if rising_edge(CLK)  then
            if (RST='1') then
                present_state <= S_IDLE;
            else
                present_state <= next_state;
            end if;
        end if;
    end process;

    process (present_state, INPUT_EN, CNT_MT_OVER, ALL_THREADS_FINISHED)
    begin
        INIT1 <= '0';
        INIT2 <= '0';
        WORK <= '0';
        FINISH <= '0';

        case present_state is
        when S_IDLE =>
            next_state <= S_IDLE;
            if(INPUT_EN ='1') then
                next_state <= S_ITER_INIT;
                INIT1 <= '1';
            end if;  
        when S_ITER_INIT =>
            next_state <= S_ITER_INIT;
            INIT1 <= '1';
            INIT2 <= '1';
            if (CNT_MT_OVER = '1') then
                INIT1 <= '0';
                next_state <= S_RUN;
            end if;
        when S_RUN =>
            next_state <= S_RUN;
            WORK <= '1';
            if (ALL_THREADS_FINISHED = '1') then
                WORK <= '0';
                next_state <= S_IDLE;
                FINISH <= '1';
            end if;
        when others =>
            next_state <= S_IDLE;    
        end case;
    end process;

end behavioral;
