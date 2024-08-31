<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

  <!-- Output settings to generate plain text -->
  <xsl:output method="text" encoding="UTF-8"/>

  <!-- Match the root element -->
  <xsl:template match="/">
    <!-- Apply templates to each 'net' element -->
    <xsl:apply-templates select="//net/node[@ref='U1']"/>
  </xsl:template>

  <!-- Template to match 'node' elements with ref='U1' -->
  <xsl:template match="node">
    NET "<xsl:value-of select="translate(../@name, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')"/>" LOC="<xsl:value-of select="@pin"/>";
    <xsl:text>&#10;</xsl:text> <!-- New line -->
  </xsl:template>

</xsl:stylesheet>
