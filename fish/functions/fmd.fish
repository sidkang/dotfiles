function fmd -d "Format Markdown with autocorrect and prettier"
    if test (count $argv) -eq 0
        echo "Usage: fmd <file.md> [file2.md ...]"
        return 1
    end

    if not command -q autocorrect
        echo "autocorrect: command not found" >&2
        return 1
    end

    if not command -q prettier
        echo "prettier: command not found" >&2
        return 1
    end

    set -l files
    for file in $argv
        if string match -rq '\.(md|markdown|mdx|txt)$' -- $file
            set -a files $file
        else
            echo "skip non-markdown/text file: $file" >&2
        end
    end

    if test (count $files) -eq 0
        echo "no markdown or text files found" >&2
        return 1
    end

    autocorrect --fix $files
    or return $status

    prettier --write $files
    or return $status

    printf '%s\n' $files
end
