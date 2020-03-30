from inspect import Parameter
from typing import Type, Union, Dict


_type_display_name_map: Dict[Type, str] = {
    str: 'str',
    int: 'int',
    float: 'float',
}


def get_type_display_name(type_: Type) -> str:
    if type_ in _type_display_name_map:
        return _type_display_name_map[type_]
    return type_.__name__


def get_parameter_expected_type(parameter: Parameter) -> Type:
    if args := getattr(parameter.annotation, '__args__', None):
        # Catch Optional[type] types, and return the type.
        if args is not None and len(args) == 2 and args[1] is type(None):
            return args[0]
    return parameter.annotation
