function rbw -d "Wrapper around rbw get using local id index"
    # Only optimize `rbw get <name>`; everything else should behave like raw rbw.
    if test (count $argv) -eq 0
        command rbw
        return $status
    end

    if test "$argv[1]" != get
        command rbw $argv
        return $status
    end

    if test (count $argv) -lt 2
        command rbw $argv
        return $status
    end

    set -l passthrough get
    set -l needle
    set -l expecting_field_value 0

    for arg in $argv[2..-1]
        if test -n "$needle"
            set passthrough $passthrough "$arg"
            continue
        end

        if test $expecting_field_value -eq 1
            set passthrough $passthrough "$arg"
            set expecting_field_value 0
            continue
        end

        switch "$arg"
            case --field -f
                set passthrough $passthrough "$arg"
                set expecting_field_value 1
            case '*'
                if test -z "$needle"; and not string match -q -- '-*' "$arg"
                    set needle "$arg"
                else
                    command rbw $argv
                    return $status
                end
        end
    end

    if test -z "$needle"
        command rbw $argv
        return $status
    end

    if string match -rq '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$' -- "$needle"
        command rbw $argv
        return $status
    end

    # If the index is missing, fall back to raw rbw so rebuilding stays explicit.
    if test -z "$RBW_INDEX_FILE" -o -z "$RBW_INDEX_PASSWORD"
        command rbw $argv
        return $status
    end

    if not command -q openssl; or not test -f "$RBW_INDEX_FILE"
        command rbw $argv
        return $status
    end

    set -l tab (printf '\t')
    set -l matches (command openssl enc -d -aes-256-cbc -pbkdf2 -pass pass:"$RBW_INDEX_PASSWORD" -in "$RBW_INDEX_FILE" 2>/dev/null | while read -l line
        set -l parts (string split -m 1 "$tab" -- "$line")
        if test (count $parts) -eq 2; and test "$parts[1]" = "$needle"
            echo "$parts[2]"
        end
    end)

    # Fall back to raw rbw if the local index is unavailable or misses this entry.
    if test $status -ne 0 -o (count $matches) -eq 0
        command rbw $argv
        return $status
    end

    # Duplicate names are ambiguous, so stop instead of guessing the wrong secret.
    if test (count $matches) -gt 1
        echo "duplicate rbw entry names: $needle" >&2
        printf '%s\n' $matches >&2
        return 1
    end

    set -l entry_id "$matches[1]"

    command rbw $passthrough "$entry_id"
end
