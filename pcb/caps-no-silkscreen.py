from kiutils.board import Board
from kiutils.items.fpitems import FpText
import pprint

file = 'picox-8.kicad_pcb'

# Load the PCB file
pcb = Board().from_file(file)

# Define the mapping from silkscreen layers to Fab layers
layer_mapping = {
  'F.SilkS': 'F.Fab',
  'B.SilkS': 'B.Fab'
}

for footprint in pcb.footprints:
  if footprint.libraryNickname == 'Resistor_SMD':
    for item in footprint.graphicItems:
      if isinstance(item, FpText) and item.type == 'reference':
        print('hiding', item.text)
        item.hide = True

# Save the modified PCB file
pcb.to_file(file)
