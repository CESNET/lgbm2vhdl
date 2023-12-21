library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;
use ieee.std_logic_textio.all;
use ieee.numeric_std.all;
use std.textio.all;
use ieee.fixed_float_types.all;
use ieee.fixed_pkg.all;
use std.env.stop;
use work.dtype_pkg.all;

-- ----------------------------------------------------------------------------
--                        Entity declaration
-- ----------------------------------------------------------------------------
entity testbench is
end entity testbench;

-- ----------------------------------------------------------------------------
--                      Architecture declaration
-- ----------------------------------------------------------------------------
architecture behavioral of testbench is

   file file_inputs     : text;
   file file_outputs    : text;

   signal clk          : std_logic;
   signal rst          : std_logic;

   signal start        : std_logic;
   signal finish       : std_logic;

   signal mi_in_wr     : std_logic;
   signal mi_in_waddr  : std_logic_vector({mi_in_addr_size}-1 downto 0);
   signal mi_in_wdata  : std_logic_vector({mi_in_data_size}-1 downto 0);

   signal mi_out_raddr : std_logic_vector({mi_out_addr_size}-1 downto 0);
   signal mi_out_rdata : std_logic_vector({mi_out_data_size}-1 downto 0);

   constant clkper  : time := 10 ns;

-- ----------------------------------------------------------------------------
--                      Architecture body
-- ----------------------------------------------------------------------------
begin

   uut : entity work.wrapper
   port map(clk, rst, start, finish, mi_in_wr, mi_in_waddr, mi_in_wdata, mi_out_raddr, mi_out_rdata);

   -- -------------------------------------------------------------
   -- clk clock generator
   clkfgen : process
   begin
      clk <= '1';
      wait for clkper/2;
      clk <= '0';
      wait for clkper/2;
   end process;

   -- ----------------------------------------------------------------------------
   --                         Main testbench process
   -- ----------------------------------------------------------------------------
   tb : process
      variable v_ILINE     : line;
      variable v_OLINE     : line;
      variable mi_waddr    : std_logic_vector({mi_in_addr_size}-1 downto 0);
      variable mi_wdata    : std_logic_vector({mi_in_data_size}-1 downto 0);
      variable mi_raddr    : std_logic_vector({mi_out_addr_size}-1 downto 0);
      variable mi_rdata    : std_logic_vector({mi_out_data_size}-1 downto 0);
   begin
      file_open(file_inputs, "input_data.txt",  read_mode);
      file_open(file_outputs, "output_data.txt", write_mode);

      rst <= '1';
      start <= '0';
      mi_in_wr <= '0';
      mi_in_wdata <= (others => '0');
      mi_in_waddr <= (others => '0');
      mi_out_raddr <= (others => '0');
      wait for 40 ns;
      rst <= '0';

      -- ------------------------------------------------------------
      -- Write input features
      mi_waddr := (others => '0');
      while not endfile(file_inputs) loop
         readline(file_inputs, v_ILINE);
         read(v_ILINE, mi_wdata);
    
         mi_in_wdata <= mi_wdata;
         mi_in_waddr <= mi_waddr;
         mi_in_wr <= '1';
         wait for clkper;
         mi_waddr := mi_waddr + 1;
      end loop;
      mi_in_wr <= '0';
      mi_in_wdata <= (others => '0');
      mi_in_waddr <= (others => '0');
    
      file_close(file_inputs);

      -- ------------------------------------------------------------
      -- Start calculation
      wait for 2*clkper;
      start <= '1';
      wait for clkper;
      start <= '0';
      
      -- ------------------------------------------------------------
      -- Wait until finish
      wait until finish = '1';
      wait for 100 ns;

      -- ------------------------------------------------------------
      -- Read output class data
      mi_raddr := (others => '0');
      for i in 0 to {num_classes}-1 loop
         mi_out_raddr <= mi_raddr;
         wait for clkper;
         mi_rdata := mi_out_rdata;
         write(v_OLINE, mi_rdata);
         writeline(file_outputs, v_OLINE);
         mi_raddr := mi_raddr + 1;
      end loop;
      mi_out_raddr <= (others => '0');

      -- ------------------------------------------------------------
      -- Finish simulation
      file_close(file_outputs);
      stop;
   end process;

end architecture behavioral;
