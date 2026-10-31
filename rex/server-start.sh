#!/bin/sh
# Start the Rex server with anonymous HTTP listeners.
# cube listens only on its LAN address; glacier listens on the VPN and LAN addresses.
# `rex server start` is idempotent: a running server keeps its own listeners.
rex="$HOME/Library/Application Support/com.superlogical.rex/RexServer/Versions/Current/Rex Server.app/Contents/MacOS/rex"
port=7297

vpn=10.8.0.1
lan=
vpn_up=
host=$(scutil --get LocalHostName)
for _ in $(seq 30); do
  lan=$(ipconfig getifaddr en0)
  case "$host" in
    cube) [ "$lan" = 10.0.1.12 ] && break ;;
    glacier)
      ifconfig | grep -q "inet $vpn " && vpn_up=1
      [ -n "$lan" ] && [ -n "$vpn_up" ] && break ;;
    *) lan=; break ;;
  esac
  sleep 1
done
[ "$host" = cube ] && [ "$lan" != 10.0.1.12 ] && lan=

set -- --allow-anonymous
[ -n "$vpn_up" ] && set -- "$@" --extra-listen "http://$vpn:$port"
[ -n "$lan" ] && set -- "$@" --extra-listen "http://$lan:$port"
exec "$rex" server start "$@"
