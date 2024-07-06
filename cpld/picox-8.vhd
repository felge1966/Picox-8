library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.STD_LOGIC_ARITH.ALL;
use IEEE.STD_LOGIC_UNSIGNED.ALL;

entity PicoX8 is
    Port (
        clk       : in  std_logic;                   -- System clock
        ioreq     : in  std_logic;                   -- I/O request signal
        rd        : in  std_logic;                   -- Read signal
        address   : in  std_logic_vector(7 downto 0);-- Address bus (8-bit for I/O)
        data      : inout std_logic_vector(7 downto 0) -- Data bus (8-bit)
    );
end PicoX8;

architecture Behavioral of PicoX8 is
    constant FIXED_VALUE : std_logic_vector(7 downto 0) := "10101010"; -- Fixed value to return
    signal data_out      : std_logic_vector(7 downto 0); -- Internal signal for data bus
    signal oe            : std_logic; -- Output enable signal
begin
    process(clk)
    begin
        if rising_edge(clk) then
            if (ioreq = '0') and (rd = '0') and (address = "10000110") then -- I/O read at address 86h
                data_out <= FIXED_VALUE;
                oe <= '1';
            else
                oe <= '0';
            end if;
        end if;
    end process;

    -- Drive the data bus with the fixed value when output enable is active
    data <= data_out when oe = '1' else (others => 'Z');
end Behavioral;

