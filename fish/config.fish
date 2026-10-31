######################### ENV ################################################
set -gx HOMEBREW_NO_AUTO_UPDATE 1
set -gx HOMEBREW_NO_ANALYTICS 1
set -gx HOMEBREW_NO_INSTALL_CLEANUP 1
set -gx LC_ALL en_US.UTF-8
set -gx LANG en_US.UTF-8
set -gx EDITOR nvim
set -gx LOCAL_HOSTNAME $hostname

function fish_greeting
    echo (set_color -o -i green; echo Yo......)
end

function fish_title
    set -l cwd (string replace -- $HOME '~' (pwd))

    if test (count $argv) -gt 0; and test -n "$argv[1]"
        echo "$argv[1] · $cwd"
    else
        echo $cwd
    end
end

######################### XDG ################################################
set -gx XDG_CONFIG_HOME $HOME/.config
set -gx XDG_CACHE_HOME $HOME/.cache
set -gx XDG_DATA_HOME $HOME/.local/share
set -gx XDG_STATE_HOME $HOME/.local/state

set -gx DSH_HOME $HOME/.config/dsh

set -gx LARKSUITE_CLI_CONFIG_DIR $HOME/.config/lark-cli

######################### TOOL ENV ###########################################
set -gx JUPYTER_CONFIG_DIR $XDG_CONFIG_HOME/jupyter
set -gx IPYTHONDIR $XDG_CONFIG_HOME/ipython
set -gx PI_SKIP_VERSION_CHECK 1
set -q PI_CODING_AGENT_DIR; or set -gx PI_CODING_AGENT_DIR $HOME/.config/pi/agent

if command -q julia
    set -gx JULIA_DEPOT_PATH $XDG_DATA_HOME/julia
end

if command -q claude
    set -gx DISABLE_AUTOUPDATER 1
end

########################## PATH ################################################
if test -e /opt/homebrew/bin/brew
    set -gx HOMEBREW_PREFIX /opt/homebrew
    set -gx HOMEBREW_CELLAR /opt/homebrew/Cellar
    set -gx HOMEBREW_REPOSITORY /opt/homebrew
    # set -gx HOMEBREW_CORE_GIT_REMOTE https://mirrors.tuna.tsinghua.edu.cn/git/homebrew/homebrew-core.git

    fish_add_path -g /opt/homebrew/bin /opt/homebrew/sbin
    set -q INFOPATH; or set -gx INFOPATH
    contains /opt/homebrew/share/info $INFOPATH; or set -gx INFOPATH /opt/homebrew/share/info $INFOPATH
else if test -e /home/linuxbrew/.linuxbrew/bin/brew
    eval (/home/linuxbrew/.linuxbrew/bin/brew shellenv fish)
end

if test -d /Library/TeX/texbin
    fish_add_path -g /Library/TeX/texbin
end

if test -d /opt/homebrew/opt/openjdk/bin
    fish_add_path -g /opt/homebrew/opt/openjdk/bin
end

if test -d /opt/homebrew/opt/grep/libexec/gnubin
    fish_add_path -g /opt/homebrew/opt/grep/libexec/gnubin
end

if test -d /Applications/quarto/bin
    fish_add_path -g /Applications/quarto/bin
end

if test -x /Applications/Surge.app/Contents/Applications/surge-cli
    fish_add_path -g /Applications/Surge.app/Contents/Applications
end

if test -d /Applications/Espanso.app/Contents/MacOS
    fish_add_path -g /Applications/Espanso.app/Contents/MacOS
end

if test -d /Applications/Obsidian.app/Contents/MacOS
    fish_add_path -g /Applications/Obsidian.app/Contents/MacOS
end

if test -x '/Applications/Rex Beta.app/Contents/Helpers/Rex Server.rex/Contents/MacOS/rex'
    fish_add_path -g '/Applications/Rex Beta.app/Contents/Helpers/Rex Server.rex/Contents/MacOS'
else if test -x '/Applications/Rex.app/Contents/Helpers/Rex Server.rex/Contents/MacOS/rex'
    fish_add_path -g '/Applications/Rex.app/Contents/Helpers/Rex Server.rex/Contents/MacOS'
end

if test -d /opt/homebrew/opt/rustup/bin
    fish_add_path -g /opt/homebrew/opt/rustup/bin
end

if test -d $HOME/.cargo/bin
    fish_add_path -g $HOME/.cargo/bin
end

if test -d $HOME/.local/bin
    fish_add_path -g $HOME/.local/bin
end

set -gx CODEX_HOME $HOME/.config/codex

########################## FUNCTIONS ############################################
function dotclean
    set -l target .
    if test (count $argv) -gt 0
        set target $argv[1]
    end

    find "$target" \( -name ".Trashes" -o -name ".Spotlight-V100" -o -name ".fseventsd" -o -name ".TemporaryItems" -o -name ".DS_Store" -o -name ".apdisk" -o -name "._*" ! -name "._." \) -exec rm -rf {} +
end

########################## INTERACTIVE INIT ####################################

status is-interactive; or return

############### KEY BINDs

bind -e \ee
bind -e \ev
bind \coe edit_command_buffer
bind ctrl-backspace history-delete
bind ctrl-y accept-autosuggestion
bind \cn history-search-forward
bind \cp history-search-backward
bind \c\[ history-prefix-search-forward
bind \c\] history-prefix-search-backward
bind \e\[B history-search-forward
bind \e\[A history-search-backward

if test -e /Applications/OrbStack.app
    source ~/.orbstack/shell/init2.fish 2>/dev/null || :
end

if command -q zoxide
    set -gx _ZO_EXCLUDE_DIRS $XDG_DATA_HOME $XDG_STATE_HOME $XDG_CACHE_HOME
    set -gx _ZO_EXCLUDE_PATHS ".git" ".jj"
    zoxide init fish --hook pwd | source
end

if command -q starship
    starship init fish | source
end

if command -q gh; and not set -qx GH_TOKEN
    set -gx GH_TOKEN (gh auth token)
end

########################## INTERACTIVE ABBRS ####################################
if command -q brew
    abbr -a bu "brew update && brew upgrade -y && brew cleanup"
end

if command -q nvim
    abbr -a v nvim
end

if command -q fastfetch
    abbr -a neofetch fastfetch
end

abbr -a g2u "iconv -c -f GB2312 -t UTF-8"
abbr -a copy --set-cursor=! "! | tr -d '\n' | pbcopy"
abbr -a conv --set-cursor=! "echo '!' | iconv -f UTF-8-Mac -t latin1 | iconv -f gbk"
abbr -a reload_fish source ~/.config/fish/config.fish

if command -q pi
    abbr -a pisbx 'PI_CODING_AGENT_DIR=(path dirname "$PI_CODING_AGENT_DIR")/sbx-agent pi'
end

if command -q eza
    abbr -a ls eza
    abbr -a la eza -a
    abbr -a ll eza -l --time-style=iso --group-directories-first
    abbr -a lla eza -l --time-style=iso --group-directories-first --all
    abbr -a lls eza -l --time-style=iso --group-directories-first --total-size
    abbr -a llas eza -l --time-style=iso --group-directories-first --all --total-size
    abbr -a llt eza -l --time-style=iso --group-directories-first --tree
    abbr -a llat eza -l --time-style=iso --group-directories-first --all --tree
    abbr -a llast eza -l --time-style=iso --group-directories-first --all --total-size --tree
end

if command -q bat
    set -gx MANPAGER "sh -c 'col -bx | bat -l man -p'"
    #     abbr -a --position anywhere cat bat --paging=never
end

if command -q fd
    abbr -a fdds fd -H .DS_Store -tf -X rm
end

if command -q jj
    abbr -a jjbc jj bookmark create
    abbr -a jjbs jj bookmark set
    abbr -a jjbd jj bookmark delete
    abbr -a jjbl jj bookmark list
    abbr -a jjbm jj bookmark move
    abbr -a jjst jj status
    abbr -a jjlog jj log
    abbr -a jjdm --set-cursor=@ jj describe -m '@'
    abbr -a jjcm jj commit -m
end

if command -q zellij
    abbr -a zja zellij attach --create
    abbr -a zjd zellij delete-session
    abbr -a zjda zellij delete-all-sessions
    abbr -a zjk zellij kill-session
    abbr -a zjka zellij kill-all-sessions
    abbr -a zjls zellij list-sessions
    abbr -a zjw zellij watch
end

if command -q zoxide
    abbr -a za zoxide add
    # abbr -a zq zoxide query
    abbr -a zr zoxide remove
end

abbr -a vim nvim

abbr ts tailscale

abbr -a yt4 "yt-dlp -f \"bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4\""

function cq
    mkdir -p /tmp/ai-chat
    pushd /tmp/ai-chat >/dev/null
    codex exec --skip-git-repo-check --ephemeral "$argv"
    popd >/dev/null
end

function gq
    mkdir -p /tmp/gemini-chat
    pushd /tmp/gemini-chat >/dev/null
    gemini -p $argv
    set -l rc $status
    popd >/dev/null
    return $rc
end

function ocli --description "Run OpenClaw CLI in docker compose"
    begin
        cd ~/services/openclaw/openclaw-setup || return 1
        docker compose run --rm openclaw-cli $argv
    end
end

########################## INTEGRATIONS #########################################
# status is-interactive; and source $__fish_config_dir/iterm2_shell_integration.fish

########################## REFERENCE ############################################
# fish_add_path "/Users/sid/.local/share/../bin"

# Backup platform-specific brew bootstrap reference.
# switch (uname -a)
#     case "*Linux*x86_64*"
#         # eval (/home/linuxbrew/.linuxbrew/bin/brew shellenv)
#     case "*x86_64*"
#     case "*arm64*"
#         # eval (/opt/homebrew/bin/brew shellenv)
#     case "*"
#         echo something wrong.
#         return 1
# end
