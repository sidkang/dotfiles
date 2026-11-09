#!/bin/sh
# Run the Sparkle-updated Rex helper in the foreground so launchd KeepAlive
# can restart it on crash. glacier: VPN only. cube: both LAN addresses.
# Other hosts: no network listener.
rex=
for p in \
  "/Applications/Rex Beta.app/Contents/Helpers/Rex Server.rex/Contents/MacOS/rex" \
  "/Applications/Rex.app/Contents/Helpers/Rex Server.rex/Contents/MacOS/rex" \
  "$HOME/Library/Application Support/com.superlogical.rex/RexServer/Versions/Current/Rex Server.app/Contents/MacOS/rex"
do
  if [ -x "$p" ]; then
    rex=$p
    break
  fi
done
[ -n "$rex" ] || exit 1
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
exec "$rex" server run "$@"
