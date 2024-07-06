library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.STD_LOGIC_ARITH.ALL;
use IEEE.STD_LOGIC_UNSIGNED.ALL;

entity PicoX8 is
  Port (
    clk       : in  std_logic;                   -- System clock
    ioreq_n   : in  std_logic;                   -- I/O request signal
    rd_n      : in  std_logic;                   -- Read signal
    address   : in  std_logic_vector(7 downto 0);-- Address bus (8-bit for I/O)
    data      : inout std_logic_vector(7 downto 0) -- Data bus (8-bit)
    );
end PicoX8;

architecture Behavioral of PicoX8 is
  constant SERIAL_STATUS : std_logic_vector(7 downto 0) := "00000001"; -- modem, carrier
  constant IO_ADDRESS    : std_logic_vector(7 downto 0) := x"86";
  signal data_out        : std_logic_vector(7 downto 0);
  signal oe              : std_logic;
begin
  process(clk)
  begin
    if rising_edge(clk) then
      if (ioreq_n = '0') and (rd_n = '0') and (address = IO_ADDRESS) then
        data_out <= SERIAL_STATUS;
        oe <= '1';
      else
        oe <= '0';
      end if;
    end if;
  end process;

  data <= data_out when oe = '1' else (others => 'Z');
end Behavioral;

