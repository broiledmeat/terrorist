from inspect import Parameter
import textwrap
from typing import Optional, Iterable, Tuple, List


def init():
    from .commands import register
    register(name='list', description='List all commands', completion_output=False)(list_commands)
    register(name='help', description='See command usage', completion_output=False)(command_usage)


def list_commands(namespace: Optional[str] = None):
    from .commands import get_all

    filter_name: Optional[str] = f'{namespace}.' if namespace is not None else None
    command_list: List[Tuple[str, str]] = []

    for command in get_all():
        fullname: str = command.fullname()

        if filter_name is not None and not fullname.lower().startswith(filter_name):
            continue

        parameters: Iterable[Parameter] = command.signature().parameters.values()
        has_flags: bool = False
        usage: str = fullname

        for parameter in parameters:
            if parameter.kind == Parameter.KEYWORD_ONLY:
                has_flags = True
            elif parameter.default != Parameter.empty:
                usage += f' [{parameter.name}]'
            else:
                usage += f' {parameter.name}'

        if has_flags:
            usage += ' [FLAGS]'

        command_list.append((usage, command.description))

    usage_max_width: int = max([32] + [len(usage) for usage, _ in command_list])

    for usage, description in command_list:
        print(f'{usage:>{usage_max_width}}\t{description}')


def command_usage(name: str):
    from .commands import Command, RunCommandException, get
    from .types import get_type_display_name, get_parameter_expected_type

    commands: List[Command] = get(name)

    if len(commands) == 0:
        raise RunCommandException(f'No command {name}')
    elif len(commands) > 1:
        raise RunCommandException(f'Found conflicting commands: {", ".join(c.fullname() for c in commands)}')

    command: Command = commands[0]
    usage: str = command.fullname()
    parameters: Iterable[Parameter] = command.signature().parameters.values()

    for parameter in parameters:
        type_name: str = get_type_display_name(get_parameter_expected_type(parameter))

        if parameter.kind == Parameter.KEYWORD_ONLY:
            usage += f' [--{parameter.name}'
            if type_name != 'bool':
                usage += f' {type_name}'
            usage += ']'
        elif parameter.default != Parameter.empty:
            usage += f' [{parameter.name}:{type_name}={parameter.default}]'
        else:
            usage += f' {parameter.name}:{type_name}'

    print(usage)

    if command.description != '':
        print(command.description)

    if command.function.__doc__ is not None:
        print()
        print(textwrap.dedent(command.function.__doc__).strip())
