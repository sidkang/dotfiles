local M = {}

local applescripts = {
	xnip_capture = [[
tell application "System Events"
  tell process "Xnip"
    click menu item 1 of menu 1 of menu bar item 1 of menu bar 2
  end tell
end tell
]],
}

local function notify(message)
	hs.alert.show(message)
end

local function runAppleScript(name)
	local script = applescripts[name]
	if script == nil then
		notify("AppleScript not found")
		return
	end

	local ok, _, err = hs.osascript.applescript(script)
	if not ok then
		notify(err or "AppleScript failed")
	end
end

function M.setup(route)
	hs.urlevent.bind(route, function(_, params)
		local name = params["name"]
		if name == nil then
			notify("Missing AppleScript name")
			return
		end

		runAppleScript(name)
	end)
end

return M
