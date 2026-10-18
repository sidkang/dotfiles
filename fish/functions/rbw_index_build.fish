function rbw_index_build -d "Build encrypted rbw name to id index"
    if not command -q rbw
        echo "rbw: command not found" >&2
        return 1
    end

    if not command -q openssl
        echo "openssl: command not found" >&2
        return 1
    end

    if test -z "$RBW_INDEX_FILE" -o -z "$RBW_INDEX_PASSWORD"
        echo "RBW_INDEX_FILE or RBW_INDEX_PASSWORD is not set" >&2
        return 1
    end

    # Keep the local name->id cache encrypted because it mirrors vault entry names.
    set -l index_file "$RBW_INDEX_FILE"
    set -l tab (printf '\t')
    mkdir -p (dirname "$index_file")

    command rbw list --fields id,name | while read -l line
        set -l parts (string split -m 1 "$tab" -- "$line")
        if test (count $parts) -eq 2
            printf '%s\t%s\n' "$parts[2]" "$parts[1]"
        end
    end | command openssl enc -aes-256-cbc -pbkdf2 -salt -pass pass:"$RBW_INDEX_PASSWORD" -out "$index_file"

    if test $status -ne 0
        echo "failed to build rbw index" >&2
        return 1
    end
end
