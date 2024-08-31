import xml.etree.ElementTree as ET
from xml.dom import minidom
from pyparsing import nestedExpr
import sys
import os

# Function to parse the S-expression netlist
def parse_netlist(netlist_content):
    netlist = nestedExpr().parseString(netlist_content).asList()
    return netlist

# Function to strip quotes from attribute values
def strip_quotes(value):
    return value.strip('"')

# Function to convert parsed netlist to XML
def convert_to_xml(parsed_netlist):
    root = ET.Element("netlist")

    # Find the 'nets' section in the parsed netlist
    for section in parsed_netlist[0]:
        if section[0] == 'nets':
            for net in section[1:]:
                if net[0] == 'net':
                    net_code = None
                    net_name = None
                    nodes = []

                    # Extract net attributes and nodes
                    for entry in net[1:]:
                        if entry[0] == 'code':
                            net_code = strip_quotes(entry[1])
                        elif entry[0] == 'name':
                            net_name = strip_quotes(entry[1])
                        elif entry[0] == 'node':
                            node_attrs = {}
                            for attr in entry[1:]:
                                node_attrs[attr[0]] = strip_quotes(attr[1])
                            nodes.append(node_attrs)

                    # Create XML element for the net
                    if net_code is not None and net_name is not None:
                        net_elem = ET.SubElement(root, "net", code=net_code, name=net_name)

                        # Add nodes to the net
                        for node_attrs in nodes:
                            ET.SubElement(net_elem, "node", **node_attrs)

    return ET.ElementTree(root)

# Function to prettify (indent) the XML
def prettify_xml(elem):
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

# Function to save XML to a file
def save_xml(xml_tree, filename):
    xml_string = prettify_xml(xml_tree.getroot())
    with open(filename, 'w') as f:
        f.write(xml_string)

# Main function to load, parse, convert and save the netlist
def main(input_filename):
    # Load the S-expression netlist file
    with open(input_filename, 'r') as file:
        netlist_content = file.read()

    # Parse the S-expression netlist
    parsed_netlist = parse_netlist(netlist_content)

    # Convert the parsed netlist to XML
    xml_tree = convert_to_xml(parsed_netlist)

    # Create the output file name with .xml extension
    output_filename = os.path.splitext(input_filename)[0] + '.xml'

    # Save the XML to the output file
    save_xml(xml_tree, output_filename)
    print(f"XML file generated: {output_filename}")

if __name__ == "__main__":
    # Ensure the script is called with the input file argument
    if len(sys.argv) != 2:
        print("Usage: python your_script.py input_file.net")
        sys.exit(1)

    input_filename = sys.argv[1]
    main(input_filename)
