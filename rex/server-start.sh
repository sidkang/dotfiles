#!/bin/sh
# Run the Sparkle-updated Rex helper in the foreground so launchd KeepAlive
# keeps it running. glacier: VPN only. cube: both LAN addresses.
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
endpoint="unix://$HOME/Library/Application Support/rex/server.sock"

port=7297

case $(scutil --get LocalHostName) in
  glacier) addrs="10.8.0.1" ;;
  cube) addrs="10.0.1.12 10.0.1.112" ;;
  *) addrs= ;;
esac

want=0
for a in $addrs; do want=$((want + 1)); done

# Wait for every address; let launchd retry if the VPN is still unavailable.
for _ in $(seq 30); do
  set --
  have=$(ifconfig)
  for a in $addrs; do
    case $have in *"inet $a "*) set -- "$@" --extra-listen "http://$a:$port" ;; esac
  done
  [ $(($# / 2)) -eq "$want" ] && break
  sleep 1
done

[ $(($# / 2)) -eq "$want" ] || exit 1
[ $# -gt 0 ] && set -- --allow-anonymous "$@"

# exec preserves this PID. Open the app only once this server answers, not
# merely when another process happens to hold the socket.
server_pid=$$
(
  for _ in $(seq 60); do
    kill -0 "$server_pid" 2>/dev/null || exit 0
    if "$rex" -S "$endpoint" --autostart=false --timeout 2s server status 2>/dev/null |
      grep -qx "pid: $server_pid"; then
      pgrep -x Rex >/dev/null && exit 0
      for app in "/Applications/Rex Beta.app" "/Applications/Rex.app"; do
        [ -d "$app" ] && exec open -a "$app"
      done
      exit 1
    fi
    sleep 1
  done
  echo "rex server readiness timed out; not opening app" >&2
) &
exec "$rex" -S "$endpoint" server run "$@"
