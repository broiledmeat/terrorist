from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
from inspect import Signature, Parameter, signature
import time
from typing import Type, NoReturn, Any, Optional, Callable, Iterable, Sequence, Tuple, List, Dict, Mapping

__all__ = ('Command', 'RunCommandException', 'register', 'get', 'get_all', 'run')

CommandFunctionType = Callable[..., NoReturn]

_registered_full_names: Dict[str, Command] = {}
_registered_short_names: Dict[str, List[Command]] = defaultdict(list)


@dataclass(frozen=True)
class Command:
    namespace: Optional[str]
    name: str
    description: str
    function: CommandFunctionType
    completion_output: bool = True

    def fullname(self) -> str:
        if self.namespace is None:
            return self.name
        return f'{self.namespace}.{self.name}'

    def signature(self) -> Signature:
        return signature(self.function)


class RunCommandException(Exception):
    pass


def register(namespace: Optional[str] = None,
             name: Optional[str] = None,
             description: str = '',
             completion_output: bool = True):
    def _inner(function: CommandFunctionType):
        command: Command = Command(namespace,
                                   name or function.__name__,
                                   description,
                                   function,
                                   completion_output=completion_output)
        fullname: str = command.fullname()

        if fullname in _registered_full_names:
            raise KeyError(f'Command "{fullname} is already registered.')

        for parameter in command.signature().parameters.values():
            if parameter.annotation == Parameter.empty:
                raise TypeError(f'Command "{fullname}" parameter "{parameter.name}" must have a type annotation.')

        _registered_full_names[fullname] = command
        _registered_short_names[command.name].append(command)
        return function

    return _inner


def get_all() -> Iterable[Command]:
    return _registered_full_names.values()


def get(name: str) -> List[Command]:
    from . import config

    if name in _registered_full_names:
        return [_registered_full_names[name]]

    if config.get('terrorist', {}).get('short_name_resolution', False):
        return _registered_short_names[name]

    return []


def run(name: str, raw_args: Optional[Sequence[str]] = None):
    commands: List[Command] = get(name)

    if len(commands) == 0:
        raise RunCommandException(f'No command {name}')
    elif len(commands) > 1:
        raise RunCommandException(f'')

    command: Command = commands[0]
    args, kwargs = _process_args(command, raw_args or [])

    start_time = time.perf_counter()
    exception: Optional[Exception] = None
    try:
        command.function(*args, **kwargs)
    except Exception as e:
        exception = e
        raise e
    finally:
        end_time = time.perf_counter()
        if command.completion_output:
            print(f'{"Succeeded" if exception is None else "Failed"}: {(end_time - start_time):.03f}s')


def _process_args(command: Command, raw_args: Sequence[str]) -> Tuple[List[Any], Dict[str, Any]]:
    from .types import get_parameter_expected_type

    parameters: Mapping[str, Parameter] = command.signature().parameters
    parameter_list: List[Parameter] = list(parameters.values())

    # Find number of required arguments (the last function parameter that does not have a default.)
    num_required_args: int = 0
    num_allowed_args: int = 0
    for i, parameter in enumerate(parameter_list):
        if parameter.default == Parameter.empty:
            num_required_args = i + 1
        if parameter.kind != Parameter.KEYWORD_ONLY:
            num_allowed_args = i + 1

    # Separate out arguments and flags.
    args: List[str] = []
    kwargs: Dict[str, Any] = {}

    arg_index: int = 0
    raw_arg_index: int = 0

    while raw_arg_index < len(raw_args):
        raw_arg: str = raw_args[raw_arg_index]

        if raw_arg.startswith('--'):
            # This is a flag. (Corresponds to a keyword only parameter.)
            key: str = raw_arg[2:]

            if key not in parameters:
                raise RunCommandException(f'No flag "{key}" for command "{command.fullname()}".')

            type_: Type = get_parameter_expected_type(parameters[key])

            if type_ == bool:
                # Boolean flags don't need any additional args.
                kwargs[key] = True

            else:
                # Non boolean flags need to grab the next arg, and coerce it to the expected parameter type.
                raw_arg_index += 1

                if raw_arg_index >= len(raw_args):
                    raise RunCommandException(f'Flag "{key} requires a value.')

                kwargs[key] = _coerce_value(raw_args[raw_arg_index], type_)
        else:
            # This is a regular arg. Coerce it to the the expected parameter type.
            type_: Type = get_parameter_expected_type(parameter_list[arg_index])

            args.append(_coerce_value(raw_args[raw_arg_index], type_))
            arg_index += 1

        raw_arg_index += 1

    if not (num_required_args <= len(args) <= num_allowed_args):
        num_str = (f'{num_required_args} to {num_allowed_args}'
                   if num_required_args != num_allowed_args
                   else str(num_required_args))
        raise RunCommandException(f'Incorrect number of arguments for command "{command.fullname()}", '
                                  f'expected {num_str}')

    return args, kwargs


def _coerce_value(value: str, type_: Type) -> Any:
    try:
        return type_(value)
    except ValueError:
        from .types import get_type_display_name

        type_name: str = get_type_display_name(type_)
        raise RunCommandException(f'Could not coerce "{value}" to a "{type_name}".')
