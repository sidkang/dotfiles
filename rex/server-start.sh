#!/bin/sh
# Start the Rex server with anonymous HTTP listeners on this host's fixed addresses.
# glacier: VPN only. cube: both LAN addresses. Other hosts: no network listener.
# `rex server start` is idempotent: a running server keeps its own listeners.
rex="$HOME/Library/Application Support/com.superlogical.rex/RexServer/Versions/Current/Rex Server.app/Contents/MacOS/rex"
port=7297

case $(scutil --get LocalHostName) in
  glacier) addrs="10.8.0.1" ;;
  cube) addrs="10.0.1.12 10.0.1.112" ;;
  *) addrs= ;;
esac

want=0
for a in $addrs; do want=$((want + 1)); done

# Wait for every address to be configured, then bind only those that exist.
for _ in $(seq 30); do
  set --
  have=$(ifconfig)
  for a in $addrs; do
    case $have in *"inet $a "*) set -- "$@" --extra-listen "http://$a:$port" ;; esac
  done
  [ $(($# / 2)) -eq "$want" ] && break
  sleep 1
done

[ $# -gt 0 ] && set -- --allow-anonymous "$@"
exec "$rex" server start "$@"
