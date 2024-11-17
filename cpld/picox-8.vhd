
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
-- signal, with the RP2040 making changes only near the rising edge and
-- sampling near the falling edge.

-- FIXME: Is there a race condition with the IBF and OBF IRQ signals, i.e. do
-- they need to be delayed by a cycle to prevent buffer overwrites?

entity PicoX8 is
  Port (
    -- PX-8 expansion bus
    clk          : in    std_logic;
    iorq_n       : in    std_logic;
    rd_n         : in    std_logic;
    wr_n         : in    std_logic;
    rs_n         : in    std_logic;
    address      : in    std_logic_vector(15 downto 0);
    data         : inout std_logic_vector(7 downto 0);
    dcas         : in    std_logic;
    dw           : in    std_logic;
    off          : in    std_logic;
    bk2_n        : in    std_logic;
    busak_n      : in    std_logic;
    busrq_n      : in    std_logic;
    hlta_n       : out   std_logic;
    intex_n      : out   std_logic;
    m1_n         : in    std_logic;
    mreq_n       : in    std_logic;
    wait_n       : in    std_logic;

    -- PX-8 RS232 port (receiver needs inverter)
    rxd_n        : out   std_logic;
    txd_n        : in    std_logic;

    -- On board peripherals

    -- Battery charger
    chg_stat1    : in    std_logic;
    chg_stat2    : in    std_logic;
    chg_pg_n     : in    std_logic;

    chg_ce       : out   std_logic;
    chg_prog2    : out   std_logic;
    chg_sel      : out   std_logic;
    chg_te_n     : out   std_logic;

    -- SD Card status bits
    sd_cd        : in    std_logic;
    sd_wp        : in    std_logic;

    -- Serial transceiver control
    ser_en_n     : out   std_logic;
    ser_shdn_n   : out   std_logic;

    -- Buttons
    btn_reset    : in    std_logic;
    btn_failsafe : in    std_logic;

    -- Pico interface

    -- Pico reset & boot control
    pico_run     : out   std_logic;
    pico_bootsel : out   std_logic;

    -- Pico register access port
    pico_data    : inout std_logic_vector(7 downto 0);
    pico_addr    : in    std_logic_vector(2 downto 0);
    pico_stb     : in    std_logic;
    pico_dir     : in    std_logic;
    pico_clk     : out   std_logic;

    pico_txd0    : in    std_logic;
    pico_rxd0    : out   std_logic;

    -- LEDs for debugging
    led0         : out   std_logic;
    led1         : out   std_logic;
    led2         : out   std_logic;
    led3         : out   std_logic
    );
end PicoX8;

architecture Behavioral of PicoX8 is
  constant PX8_TONE_DIALER        : std_logic_vector(7 downto 0) := x"84";
  constant PX8_MODEM_CONTROL      : std_logic_vector(7 downto 0) := x"85";
  constant PX8_MODEM_STATUS       : std_logic_vector(7 downto 0) := x"86";
  constant PX8_RAMDISK_DATA       : std_logic_vector(7 downto 0) := x"80";
  constant PX8_RAMDISK_CONTROL    : std_logic_vector(7 downto 0) := x"81";
  constant PX8_BAUDRATE           : std_logic_vector(7 downto 0) := x"00";
  constant PX8_CTLR2              : std_logic_vector(7 downto 0) := x"02";
  constant PICO_TONE_DIALER       : std_logic_vector(2 downto 0) := "000";
  constant PICO_SERIAL_CONTROL    : std_logic_vector(2 downto 0) := "000";
  constant PICO_MODEM_CONTROL     : std_logic_vector(2 downto 0) := "001";
  constant PICO_MODEM_STATUS      : std_logic_vector(2 downto 0) := "010";
  constant PICO_RAMDISK_DATA      : std_logic_vector(2 downto 0) := "011";
  constant PICO_RAMDISK_CONTROL   : std_logic_vector(2 downto 0) := "100";
  constant PICO_BAUDRATE          : std_logic_vector(2 downto 0) := "101";
  constant PICO_MISC_CONTROL      : std_logic_vector(2 downto 0) := "110";
  constant PICO_IRQ               : std_logic_vector(2 downto 0) := "111";
  constant SERIAL_CONTROL_DEFAULT : std_logic_vector(7 downto 0) := "00000001";
  signal irq_register             : std_logic_vector(7 downto 0);
  signal modem_tone_dialer        : std_logic_vector(7 downto 0);
  signal modem_control            : std_logic_vector(7 downto 0);
  signal modem_status             : std_logic_vector(7 downto 0);
  signal baudrate                 : std_logic_vector(7 downto 0);
  signal misc_control_buf         : std_logic_vector(7 downto 0);
  signal misc_control             : std_logic_vector(7 downto 0);
  signal ramdisk_data             : std_logic_vector(7 downto 0);
  signal ramdisk_command          : std_logic_vector(7 downto 0);
  signal serial_control           : std_logic_vector(7 downto 0);
  signal irq_tone_dialer          : std_logic;
  signal irq_baudrate             : std_logic;
  signal irq_modem_control        : std_logic;
  signal irq_misc_control         : std_logic;
  signal irq_ramdisk_command      : std_logic;
  signal irq_ramdisk_obf          : std_logic;
  signal irq_ramdisk_ibf          : std_logic;
  signal data_out                 : std_logic_vector(7 downto 0);
  signal oe                       : std_logic;
  signal pico_data_out            : std_logic_vector(7 downto 0);
  signal pico_oe                  : std_logic;
  signal led1_buf                 : std_logic := '1';
  signal led2_buf                 : std_logic := '1';
  signal led3_buf                 : std_logic := '1';
begin
  process(clk)
  begin
    if falling_edge(clk) then
      if (rs_n = '0') then
        modem_tone_dialer   <= x"00";
        modem_control       <= x"00";
        modem_status        <= x"00";
        baudrate            <= x"00";
        misc_control        <= x"00";
        ramdisk_data        <= x"00";
        ramdisk_command     <= x"00";
        serial_control      <= SERIAL_CONTROL_DEFAULT;
        irq_ramdisk_ibf     <= '0';
        irq_ramdisk_obf     <= '0';
        irq_tone_dialer     <= '0';
        irq_modem_control   <= '0';
        irq_baudrate        <= '0';
        irq_misc_control    <= '0';
        irq_ramdisk_command <= '0';
        oe <= '0';
        data_out <= (others => '0');
      else
        led1_buf <= '1';
        led2_buf <= '1';
        led3_buf <= '1';
        oe <= '0';
        data_out <= (others => '0');
        pico_oe <= '0';

        -- Handle access from the Z80 side
        if (iorq_n = '0') then
          if (rd_n = '0') then
            case address(7 downto 0) is
              when PX8_MODEM_STATUS =>
                led1_buf <= '0';
                data_out <= modem_status;
                oe <= '1';
              when PX8_RAMDISK_DATA =>
                data_out <= ramdisk_data;
                irq_ramdisk_ibf <= '0';
                oe <= '1';

              when PX8_RAMDISK_CONTROL =>
                led2_buf <= '0';
                data_out <= (0 => irq_ramdisk_ibf, 1 => irq_ramdisk_obf, others => '0');
                oe <= '1';

              when others =>
                null;
            end case;
          elsif (wr_n = '0') then
            case address(7 downto 0) is
              when PX8_TONE_DIALER =>
                modem_tone_dialer <= data;
                irq_tone_dialer <= '1';
              when PX8_MODEM_CONTROL =>
                modem_control <= data;
                irq_modem_control <= '1';
              when PX8_BAUDRATE =>
                baudrate <= data;
                irq_baudrate <= '1';
              when PX8_CTLR2 =>
                -- Bit 5 in CTLR2 register switches external modem on and off
                misc_control_buf(0) <= data(5);
              when PX8_RAMDISK_DATA =>
                ramdisk_data <= data;
                irq_ramdisk_obf <= '1';

              when PX8_RAMDISK_CONTROL =>
                ramdisk_command <= data;
                irq_ramdisk_command <= '1';

              when others =>
                null;
            end case;
          end if;
        end if;
        -- Handle access from the Pico side
        if (pico_stb = '1') then
          if (pico_dir = '0') then
            pico_oe <= '1';
            case pico_addr is -- read
              when PICO_TONE_DIALER =>
                pico_data_out <= modem_tone_dialer;
                irq_tone_dialer <= '0';
              when PICO_MODEM_CONTROL =>
                pico_data_out <= modem_control;
                irq_modem_control <= '0';
              when PICO_BAUDRATE =>
                pico_data_out <= baudrate;
                irq_baudrate <= '0';
              when PICO_MISC_CONTROL =>
                pico_data_out <= misc_control;
                irq_misc_control <= '0';
              when PICO_RAMDISK_DATA =>
                pico_data_out <= ramdisk_data;
                irq_ramdisk_obf <= '0';
              when PICO_RAMDISK_CONTROL =>
                pico_data_out <= ramdisk_command;
                irq_ramdisk_command <= '0';
                irq_ramdisk_ibf <= '0';
              when PICO_IRQ =>
                pico_data_out <= irq_register;
              when others =>
                pico_data_out <= x"00";
            end case;
          else
            case pico_addr is -- write
              when PICO_MODEM_STATUS =>
                led3_buf <= '0';
                modem_status <= pico_data;
              when PICO_RAMDISK_DATA =>
                ramdisk_data <= pico_data;
                irq_ramdisk_ibf <= '1';
              when PICO_SERIAL_CONTROL =>
                serial_control <= pico_data;
              when others =>
                null;
            end case;
          end if;
        end if;
      end if;
    end if;
  end process;

  data <= data_out when oe = '1' else (others => 'Z');

  pico_data <= pico_data_out when pico_oe = '1' else (others => 'Z');
  pico_clk <= clk;

  -- RS232 RX on expansion bus needs to be inverted
  rxd_n <= not pico_txd0;
  pico_rxd0 <= txd_n;

  -- IRQ register
  irq_register <= (0 => irq_tone_dialer,
                   1 => irq_modem_control,
                   2 => irq_ramdisk_command,
                   3 => irq_ramdisk_obf,
                   4 => irq_ramdisk_ibf,
                   5 => irq_baudrate,
                   6 => irq_misc_control,
                   others => '0');

  -- Serial control bits (all bits off by default, need to set /EN and /SHDN to
  -- enable, see SERIAL_CONTROL_DEFAULT)
  ser_en_n   <= serial_control(0);
  ser_shdn_n <= serial_control(1);

  -- Buffered input bits
  misc_control_buf(1) <= btn_failsafe;

  pico_bootsel <= '1' when btn_failsafe = '0' and btn_reset = '0';
  pico_run <= btn_reset;

  led0 <= '0';
  led1 <= led1_buf;
  led2 <= not irq_ramdisk_obf;
  led3 <= not irq_ramdisk_ibf;

  -- Misc bus signals
  hlta_n  <= '1';
  intex_n <= '1';

  -- Charger control
  chg_te_n  <= '0'; -- enable safety timer
  chg_ce    <= '1'; -- enable charging
  chg_prog2 <= '1'; -- 500 mA load on USB port
  chg_sel   <= '0'; -- USB compatible

end Behavioral;
