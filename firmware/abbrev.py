def abbreviate_methods(obj, prefix):
  def get_unique_abbreviations(suffix):
    abbreviations = []
    for i in range(2, len(suffix) + 1):
      abbreviations.append(suffix[:i])
    return abbreviations

  methods_dict = {}
  duplicates = []
  for attr_name in dir(obj):
    if attr_name.startswith(prefix):
      method = getattr(obj, attr_name)
      suffix = attr_name[len(prefix):]
      abbreviations = get_unique_abbreviations(suffix)
      for abbreviation in abbreviations:
        if abbreviation in methods_dict:
          duplicates.append(abbreviation)
        else:
          methods_dict[abbreviation] = method
  for abbreviation in duplicates:
    if abbreviation in methods_dict:
      del methods_dict[abbreviation]

  return methods_dict

if __name__ == '__main__':
  # Example usage:
  class ExampleClass:
    def pre_test(self):
      print("test method")

    def pre_run(self):
      print("run method")

    def pre_read(self):
      print("read method")

  example = ExampleClass()
  methods_map = abbreviate_methods(example, "pre_")

  for key in methods_map:
    print(f"{key}: {methods_map[key]}")

  methods_map['ru']()
  methods_map['re']()
  methods_map['tes']()
