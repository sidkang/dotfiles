#!/bin/sh
set -eu

[ "$(uname -s)" = Darwin ] || exit 0

# Dock and Mission Control
defaults write com.apple.dock orientation -string right
defaults write com.apple.dock autohide -bool true
defaults write com.apple.dock show-recents -bool false
defaults write com.apple.dock minimize-to-application -bool true
defaults write com.apple.dock mineffect -string genie
defaults write com.apple.dock launchanim -bool true
defaults write com.apple.dock expose-group-apps -bool true
defaults write com.apple.spaces spans-displays -bool false

# Desktop and Stage Manager
defaults write com.apple.WindowManager GloballyEnabled -bool false
defaults write com.apple.WindowManager EnableStandardClickToShowDesktop -bool false
defaults write com.apple.WindowManager StandardHideDesktopIcons -bool false
defaults write com.apple.WindowManager HideDesktop -bool true
defaults write com.apple.WindowManager StandardHideWidgets -bool false
defaults write com.apple.WindowManager StageManagerHideWidgets -bool false
defaults write com.apple.finder ShowHardDrivesOnDesktop -bool false
defaults write com.apple.finder ShowExternalHardDrivesOnDesktop -bool true
defaults write com.apple.finder ShowRemovableMediaOnDesktop -bool true

configure_trackpad() {
    /usr/bin/defaults write "$1" TrackpadThreeFingerDrag -bool true
    /usr/bin/defaults write "$1" Clicking -bool true
    /usr/bin/defaults write "$1" TrackpadRightClick -bool true
    /usr/bin/defaults write "$1" TrackpadCornerSecondaryClick -int 0
}

/usr/bin/defaults -currentHost write NSGlobalDomain com.apple.mouse.tapBehavior -int 1
/usr/bin/defaults -currentHost write NSGlobalDomain com.apple.trackpad.enableSecondaryClick -bool true
configure_trackpad com.apple.driver.AppleBluetoothMultitouch.trackpad
model=$(/usr/sbin/system_profiler -xml SPHardwareDataType | /usr/bin/plutil -extract 0._items.0.machine_name raw -o - -)
case "$model" in
    MacBook*) configure_trackpad com.apple.AppleMultitouchTrackpad ;;
    *) defaults write com.apple.AppleMultitouchTrackpad TrackpadThreeFingerDrag -bool true ;;
esac

echo 'Trackpad preferences written. Checking live driver state:'
state=$(/usr/sbin/ioreg -r -c AppleMultitouchDevice -l)
printf '%s\n' "$state" | awk '
    /"MultitouchPreferences" =/ {
        n++
        count = split("Clicking TrackpadRightClick TrackpadThreeFingerDrag TrackpadCornerSecondaryClick", keys)
        for (i = 1; i <= count; i++) {
            expected = (keys[i] == "TrackpadCornerSecondaryClick" ? "(0|No)" : "(1|Yes)")
            ok = $0 ~ ("\"" keys[i] "\"=" expected "[,}]")
            printf "  Trackpad %d %s: %s\n", n, keys[i], (ok ? "confirmed" : "not confirmed")
            if (!ok) failed = 1
        }
    }
    END {
        if (!n) print "  No trackpad driver preferences reported; gestures not verified."
        exit failed + 0
    }'
