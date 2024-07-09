library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.STD_LOGIC_ARITH.ALL;
use IEEE.STD_LOGIC_UNSIGNED.ALL;

-- PicoX8 implements the interface between the PX-80 expansion bus
-- interface and the RP2040.  The PX-80 reads and writes the registers
-- in the CPLD using the Z80 I/O bus protocol.  The RP2040 accesses the
-- registers using an 8 bit wide, bidirectional interface with a 3 bit address
-- bus, a direction signal ('0' => read, '1' => write) and a strobe signal.
-- Transfers from and to the Pico need to be synchronized to the Z80 clock
-- signal, with the RP2040 making changes only near the falling edge.

entity PicoX8 is
  Port (
    -- PX80 expansion bus
    clk                 : in    std_logic;
    ioreq_n             : in    std_logic;
    rd_n                : in    std_logic;
    wr_n                : in    std_logic;
    reset_n             : in    std_logic;
    address             : in    std_logic_vector(7 downto 0);
    data                : inout std_logic_vector(7 downto 0);
    -- Serial port receiver (needs inverter)
    rx_n                : out   std_logic;
    rx                  : in    std_logic;

    -- Pico interface
    -- IRQ signals
    irq_tone_dialer     : out   std_logic;
    irq_modem_control   : out   std_logic;
    irq_ramdisk_command : out   std_logic;
    irq_ramdisk_obf     : out   std_logic;
    -- Pico register access port
    pico_data           : inout std_logic_vector(7 downto 0);
    pico_addr           : in    std_logic_vector(2 downto 0);
    pico_dir            : in    std_logic;
    pico_stb            : in    std_logic
    );
end PicoX8;

architecture Behavioral of PicoX8 is
  constant ADDR_TONE_DIALER     : std_logic_vector(7 downto 0) := x"84"; -- 0
  constant ADDR_MODEM_CONTROL   : std_logic_vector(7 downto 0) := x"85"; -- 1
  constant ADDR_MODEM_STATUS    : std_logic_vector(7 downto 0) := x"86"; -- 2
  constant ADDR_RAMDISK_DATA    : std_logic_vector(7 downto 0) := x"80"; -- 3
  constant ADDR_RAMDISK_CONTROL : std_logic_vector(7 downto 0) := x"81"; -- 4
  signal data_out               : std_logic_vector(7 downto 0);
  signal modem_tone_dialer      : std_logic_vector(7 downto 0);
  signal modem_control          : std_logic_vector(7 downto 0);
  signal modem_status           : std_logic_vector(7 downto 0);
  signal ramdisk_data           : std_logic_vector(7 downto 0);
  signal ramdisk_command        : std_logic_vector(7 downto 0);
  signal ramdisk_ibf            : std_logic;
  signal ramdisk_obf            : std_logic;
  signal oe                     : std_logic;
begin
  process(clk)
  begin
    if falling_edge(clk) then
      if (reset_n = '0') then
        modem_tone_dialer   <= x"00";
        modem_control       <= x"00";
        modem_status        <= x"00";
        ramdisk_data        <= x"00";
        ramdisk_command     <= x"00";
        ramdisk_ibf         <= '0';
        ramdisk_obf         <= '0';
        irq_tone_dialer     <= '0';
        irq_modem_control   <= '0';
        irq_ramdisk_command <= '0';
      elsif (ioreq_n = '0') then
        if (rd_n = '0') then
          oe <= '1';
          if (address = ADDR_MODEM_STATUS) then
            data_out <= modem_status;
          elsif (address = ADDR_RAMDISK_DATA) then
            data_out <= ramdisk_data;
            ramdisk_ibf <= '0';
          elsif (address = ADDR_RAMDISK_CONTROL) then
            data_out <= (0 => ramdisk_ibf, 1 => ramdisk_obf, others => '0');
          else
            data_out <= x"00";
          end if;
        elsif (wr_n = '0') then
          oe <= '0';
          if (address = ADDR_TONE_DIALER) then
            modem_tone_dialer <= data;
            irq_tone_dialer <= '1';
          elsif (address = ADDR_MODEM_CONTROL) then
            modem_control <= data;
            irq_modem_control <= '1';
          elsif (address = ADDR_RAMDISK_DATA) then
            ramdisk_data <= data;
            ramdisk_obf <= '1';
          elsif (address = ADDR_RAMDISK_CONTROL) then
            ramdisk_command <= data;
            irq_ramdisk_command <= '1';
          end if;
        else
          oe <= '0';
        end if;
      end if;
    end if;
  end process;

  process(clk)
  begin
    if rising_edge(clk) and (pico_stb = '1') then

      if pico_dir = '0' and pico_addr = x"0" then
        pico_data           <= modem_tone_dialer;
        irq_tone_dialer     <= '0';

      elsif pico_dir = '0' and pico_addr = x"1" then
        pico_data           <= modem_control;
        irq_modem_control   <= '0';

      elsif pico_dir = '1' and pico_addr = x"2" then
        modem_status        <= pico_data;

      elsif pico_dir = '0' and pico_addr = x"3" then
        pico_data           <= ramdisk_data;
        ramdisk_obf         <= '0';
      elsif pico_dir = '1' and pico_addr = x"3" then
        ramdisk_data        <= pico_data;
        ramdisk_ibf         <= '1';

      elsif pico_dir = '0' and pico_addr = x"4" then
        pico_data           <= ramdisk_command;
        irq_ramdisk_command <= '0';
        ramdisk_obf         <= '0';             -- flush output buffer
      else
        pico_data           <= (others => 'Z');
      end if;
    end if;
  end process;

  data <= data_out when oe = '1' else (others => 'Z');

  -- RS232 RX on expansion bus needs to be inverted
  rx_n <= not rx;

  -- RAM-Disk handshake signals
  irq_ramdisk_obf <= ramdisk_obf;

end Behavioral;

