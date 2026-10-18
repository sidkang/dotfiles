function clean_nvim -d "Remove all neovim files"
    # rm -rf ~/.local/share/nvim
    # rm -rf ~/.local/state/nvim
    # rm -rf ~/.cache/nvim
    #
    rm -rf $XDG_STATE_HOME/nvim
    rm -rf $XDG_DATA_HOME/nvim
    rm -rf $XDG_CACHE_HOME/nvim
end
