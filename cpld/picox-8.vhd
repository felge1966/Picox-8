library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.STD_LOGIC_ARITH.ALL;
use IEEE.STD_LOGIC_UNSIGNED.ALL;

entity PicoX8 is
  Port (
    -- Serial port receiver (needs inverter)
    rx_n             : out   std_logic;
    rx               : in    std_logic;
    -- PX80 Z80 System Bus
    clk              : in    std_logic;                     -- System clock
    ioreq_n          : in    std_logic;                     -- I/O request signal
    rd_n             : in    std_logic;                     -- Read signal
    wr_n             : in    std_logic;                     -- Write signal
    address          : in    std_logic_vector(7 downto 0);  -- Address bus (8-bit for I/O)
    data             : inout std_logic_vector(7 downto 0);  -- Data bus (8-bit)
    -- IRQ signals
    irq_tone_dialer  : out   std_logic;
    irq_modem_status : out   std_logic;
    irq_ramdisk_ctl  : out   std_logic;
    irq_ramdisk_data : out   std_logic;
    -- Pico register access port
    pico_data        : inout std_logic_vector(7 downto 0);
    pico_dir         : in    std_logic;
    pico_stb         : in    std_logic
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
      else
        oe <= '0';
      end if;
    end if;
  end process;

  data <= data_out when oe = '1' else (others => 'Z');

  -- RS232 RX on expansion bus needs to be inverted
  rx_n <= not rx;

end Behavioral;

