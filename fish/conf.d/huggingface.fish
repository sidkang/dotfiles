if not set -qx HF_TOKEN; and command -q rbw; and command rbw unlocked >/dev/null 2>&1
    set -l hf_token (command rbw get hf-token 2>/dev/null)
    if test "$hf_token" != ""
        set -gx HF_TOKEN "$hf_token"
    end
end
