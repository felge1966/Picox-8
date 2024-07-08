library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.STD_LOGIC_ARITH.ALL;
use IEEE.STD_LOGIC_UNSIGNED.ALL;

entity PicoX8 is
  Port (
    -- Serial port receiver (needs inverter)
    rx_n      : out   std_logic;
    rx        : in    std_logic;
    -- PX80 Z80 System Bus
    clk       : in    std_logic;                     -- System clock
    ioreq_n   : in    std_logic;                     -- I/O request signal
    rd_n      : in    std_logic;                     -- Read signal
    address   : in    std_logic_vector(7 downto 0);  -- Address bus (8-bit for I/O)
    data      : inout std_logic_vector(7 downto 0);  -- Data bus (8-bit)
    -- Tone dialer control bits
    f0        : out std_logic;
    f1        : out std_logic;
    f2        : out std_logic;
    f3        : out std_logic;
    tone      : out std_logic;
    -- Modem control bits
    ohc       : out std_logic;
    mon       : out std_logic;
    txc       : out std_logic;
    ans       : out std_logic;
    pwr       : out std_logic;
    cct       : out std_logic
    );
end PicoX8;

architecture Behavioral of PicoX8 is
  constant SERIAL_STATUS      : std_logic_vector(7 downto 0) := "00000001"; -- modem, carrier
  constant ADDR_TONE_DIALER   : std_logic_vector(7 downto 0) := x"84";
  constant ADDR_MODEM_CONTROL : std_logic_vector(7 downto 0) := x"85";
  constant ADDR_MODEM_STATUS  : std_logic_vector(7 downto 0) := x"86";
  signal data_out             : std_logic_vector(7 downto 0);
  signal oe                   : std_logic;
begin
  process(clk)
  begin
    if falling_edge(clk) and (ioreq_n = '0') then
      if (rd_n = '0') and (address = ADDR_MODEM_STATUS) then
        data_out <= SERIAL_STATUS;
        oe <= '1';
      elsif (wr_n = '0') and (address = ADDR_TONE_DIALER) then
        f0 <= data(0);
        f1 <= data(0);
        f2 <= data(0);
        f3 <= data(0);
        tone <= data(3);
        oe <= '0';
      elsif (wr_n = '0') and (address = ADDR_MODEM_CONTROL) then
        ohc <= data(0);
        mon <= data(2);
        txc <= data(3);
        ans <= data(4);
        pwr <= data(6);
        cct <= data(7);
        oe <= '0';
      else
        oe <= '0';
      end if;
    end if;
  end process;

  data <= data_out when oe = '1' else (others => 'Z');

  -- RS232 RX on expansion bus needs to be inverted
  rx_n <= not rx;

end Behavioral;

