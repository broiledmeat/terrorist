import sys

if __name__ == '__main__':
    from . import init, commands, builtins

    init()

    if len(sys.argv) < 2:
        builtins.list_commands()
        sys.exit(0)

    try:
        commands.run(sys.argv[1], sys.argv[2:])
    except commands.RunCommandException as e:
        print(str(e))
        sys.exit(1)
