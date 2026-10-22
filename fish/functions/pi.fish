function pi --description 'Run interactive Pi in a persistent zmx session' --wraps pi
    # Scripts, redirected streams and existing zmx sessions keep normal Pi behavior.
    if not status is-interactive; or not isatty stdin; or not isatty stdout; or set -q ZMX_SESSION
        command pi $argv
        return $status
    end

    if set -q argv[1]; and contains -- $argv[1] install remove uninstall update list config auth mcp
        command pi $argv
        return $status
    end

    # Skip option values so a prompt/model/path named "--print" is not a flag.
    set -l takes_value --provider --model --api-key --thinking --models --session --session-id --fork --session-dir -n --name -t --tools -xt --exclude-tools -e --extension --skill --prompt-template --theme --use-theme --system-prompt --append-system-prompt --tui-mode
    set -l skip_value 0
    set -l mode_value 0
    for arg in $argv
        if test $mode_value -eq 1
            if test "$arg" != text
                command pi $argv
                return $status
            end
            set mode_value 0
            continue
        end
        if test $skip_value -eq 1
            set skip_value 0
            continue
        end
        switch $arg
            case --
                break
            case --mode
                set mode_value 1
            case --mode=text
                continue
            case -p --print -h --help -v --version --export --list-models '--mode=*'
                command pi $argv
                return $status
        end
        contains -- $arg $takes_value; and set skip_value 1
    end

    set -l directory (string sub -l 32 -- (string replace -ar '[^a-zA-Z0-9_-]' '-' -- (path basename "$PWD")))
    test -n "$directory"; or set directory root
    set -l sessions (command zmx list --short)
    or return $status
    set -l alphabet (string split '' abcdefghijklmnopqrstuvwxyz0123456789)
    set -l name
    while true
        set name "$directory-"(random choice $alphabet)(random choice $alphabet)
        contains -- "$name" $sessions; or break
    end

    command zmx attach "$name" (command -s pi) $argv
end
