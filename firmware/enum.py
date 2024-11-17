class Enum():
  @classmethod
  def _create_name_mapping(cls):
    return {value: name for name, value in cls.__dict__.items() if isinstance(value, int)}

  @classmethod
  def get_name(cls, value):
      name_mapping = cls._create_name_mapping()
      return name_mapping.get(value, "UNKNOWN")

