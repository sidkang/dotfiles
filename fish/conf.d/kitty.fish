# Kitty integration: worker helpers and kitten abbreviations.
status is-interactive; or return

if command -q kitten
    abbr -a ksh kitten ssh
    abbr -a kat kitten icat
end

function text_work --description "Send text to kitty worker tag"
    set -l msg (string join " " -- $argv)
    kitten @ --to unix:/tmp/kitten send-text -m var:tag=worker "$msg"
end

function run_work --description "Run a command in kitty worker"
    if test (count $argv) -eq 0
        echo "run_work: missing command" >&2
        return 1
    end

    set -l parts
    for arg in $argv
        set -a parts (string escape -- $arg)
    end

    set -l cmd (string join " " -- $parts)

    text_work $cmd
    kitten @ --to unix:/tmp/kitten send-key -m var:tag=worker enter
end

function sh_work --description "Run raw shell command in kitty worker"
    if test (count $argv) -eq 0
        echo "sh_work: missing command string" >&2
        return 1
    end

    set -l cmd (string join " " -- $argv)

    text_work $cmd
    kitten @ --to unix:/tmp/kitten send-key -m var:tag=worker enter
end
