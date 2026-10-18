function gfw
    set -xg http_proxy http://localhost:6152
    set -xg https_proxy http://localhost:6152
    set -xg all_proxy socks5://localhost:6153
    set -xg HTTP_PROXY http://localhost:6152
    set -xg HTTPS_PROXY http://localhost:6152
    set -xg ALL_PROXY socks5://localhost:6153
    echo "PROXY ON"
end
