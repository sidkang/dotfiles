set -gx HOMEBREW_NO_AUTO_UPDATE 1
set -gx HOMEBREW_NO_ANALYTICS 1
set -gx HOMEBREW_NO_INSTALL_CLEANUP 1
set -gx HOMEBREW_API_DOMAIN https://mirrors.ustc.edu.cn/homebrew-bottles/api
set -gx HOMEBREW_ARTIFACT_DOMAIN https://mirrors.ustc.edu.cn/homebrew-bottles

if test -e /opt/homebrew/bin/brew
    set -gx HOMEBREW_PREFIX /opt/homebrew
    set -gx HOMEBREW_CELLAR /opt/homebrew/Cellar
    set -gx HOMEBREW_REPOSITORY /opt/homebrew
    fish_add_path -g /opt/homebrew/bin /opt/homebrew/sbin
    set -q INFOPATH; or set -gx INFOPATH
    contains /opt/homebrew/share/info $INFOPATH; or set -gx INFOPATH /opt/homebrew/share/info $INFOPATH
else if test -e /home/linuxbrew/.linuxbrew/bin/brew
    eval (/home/linuxbrew/.linuxbrew/bin/brew shellenv fish)
end
