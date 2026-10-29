-- OmniWM key actions, run from Goku as `hsurl("wm?action=...")`.
-- Everything goes through omniwmctl; Hammerspoon adds what OmniWM lacks: real window frames for floating windows.
local M = {}

local OMNIWMCTL = "/opt/homebrew/bin/omniwmctl"
local KITTEN = "/opt/homebrew/bin/kitten"
local KITTY_SOCKET = "unix:/tmp/kitten"
local KITTY_BUNDLE_ID = "net.kovidgoyal.kitty"
local KITTY_HOTKEY_TITLE = "kitty-hotkey"
local KITTY_HOTKEY_SESSION = "hotkey"
local KITTY_HOTKEY_SCRATCHPAD = "1"
local KITTY_HOTKEY_FIT_RATIO = 0.6
local KITTY_LAUNCH_TIMEOUT = 3.0
local FLOATING_MIN_SIZE = 300
local FOCUS_RETRY_DELAY = 0.05
local FOCUS_SETTLE_TIMEOUT = 0.4
local WINDOW_FIELDS = "id,window-id,title,workspace,mode,is-focused,is-visible,is-scratchpad"
local DIRECTIONS = { left = true, right = true, up = true, down = true }
local maximized = {} -- windowId -> frame to restore

-- Workspaces are addressed by display name (Q, W, 1, ...).
local appRules = {
	obsidian = { bundleId = "md.obsidian", app = "Obsidian", home = "Q" },
	wechat = { bundleId = "com.tencent.xinWeChat", app = "WeChat", home = "1", windowTitle = "WeChat" },
	telegram = { bundleId = "ru.keepcoder.Telegram", app = "Telegram", home = "1" },
	chrome = { bundleId = "com.google.Chrome", app = "Google Chrome", home = "2" },
}

local function notify(message) hs.alert.show(message) end

local function round(value) return math.floor(value + 0.5) end

local function clamp(value, low, high) return math.max(low, math.min(value, high)) end

local function sleep(seconds) hs.timer.usleep(seconds * 1000000) end

local function waitUntil(predicate, timeout)
	local deadline = hs.timer.secondsSinceEpoch() + timeout
	while hs.timer.secondsSinceEpoch() < deadline do
		if predicate() then return true end
		sleep(FOCUS_RETRY_DELAY)
	end

	return false
end

local function shellQuote(text) return "'" .. (tostring(text):gsub("'", "'\\''")) .. "'" end

--- Runs a program without a shell's word splitting; returns ok, stdout (plus stderr when asked).
local function exec(args, mergeStderr)
	local quoted = {}
	for index, arg in ipairs(args) do
		quoted[index] = shellQuote(arg)
	end

	local output, ok = hs.execute(table.concat(quoted, " ") .. (mergeStderr and " 2>&1" or " 2>/dev/null"), false)
	return ok == true, output or ""
end

local function omni(...)
	local args = { OMNIWMCTL, ... }
	local ok, output = exec(args, true)
	if not ok then
		error(string.format("Command failed: omniwmctl %s: %s", table.concat({ ... }, " "), (output:gsub("%s+$", ""))), 0)
	end

	return output
end

local function query(...)
	local args = { OMNIWMCTL, "query", ... }
	table.insert(args, "--format")
	table.insert(args, "json")
	local ok, output = exec(args, false)
	local decoded = ok and hs.json.decode(output) or nil
	if decoded == nil or decoded.result == nil then
		error("omniwmctl query failed: " .. table.concat({ ... }, " "), 0)
	end

	return decoded.result.payload
end

local function queryWindows(...)
	local args = { "windows", ... }
	table.insert(args, "--fields")
	table.insert(args, WINDOW_FIELDS)
	return query(table.unpack(args)).windows
end

local function focusedWindowId()
	local window = queryWindows("--focused")[1]
	return window and window.id or nil
end

local function focusedWorkspace() return query("active-workspace").workspace.displayName end

--- Focus lands ~150 ms after the command.
local function waitFocused(windowId)
	return waitUntil(function() return focusedWindowId() == windowId end, FOCUS_SETTLE_TIMEOUT)
end

--- A visible floating window can pull focus back, so retry once.
local function focusWindowRobustly(windowId)
	for _ = 1, 2 do
		omni("window", "navigate", windowId)
		if waitFocused(windowId) then return end
	end

	notify("Failed to focus window " .. windowId)
end

local function nextId(ids, currentId, direction)
	local index
	for position, id in ipairs(ids) do
		if id == currentId then index = position end
	end
	if index == nil then return ids[1] end
	if direction == "next" then return ids[index % #ids + 1] end

	return ids[(index - 2) % #ids + 1]
end

local function toggleApp(name)
	local rule = appRules[name]
	if rule == nil then
		notify("Unknown app: " .. tostring(name))
		return
	end

	local matches = {}
	for _, window in ipairs(queryWindows("--bundle-id", rule.bundleId)) do
		if rule.windowTitle == nil or window.title == rule.windowTitle then table.insert(matches, window) end
	end
	if #matches == 0 then
		omni("workspace", "focus-name", rule.home)
		exec({ "/usr/bin/open", "-a", rule.app }, true)
		return
	end

	local window = matches[1]
	local workspace = window.workspace.displayName
	if workspace ~= focusedWorkspace() and workspace ~= rule.home then omni("window", "move-to-workspace", window.id, rule.home) end
	focusWindowRobustly(window.id)
end

local function findKittyHotkey()
	local matches = {}
	for _, window in ipairs(queryWindows("--bundle-id", KITTY_BUNDLE_ID)) do
		if window.title == KITTY_HOTKEY_TITLE then table.insert(matches, window) end
	end
	if #matches > 1 then notify("Multiple kitty hotkey windows found") end

	return matches[1]
end

local function launchKittyHotkey()
	local launch = {
		KITTEN, "@", "--to", KITTY_SOCKET, "launch", "--type", "os-window",
		"--os-window-title", KITTY_HOTKEY_TITLE, "--add-to-session", KITTY_HOTKEY_SESSION, "--cwd=~",
	}
	if not exec(launch, true) then
		notify("Failed to launch kitty hotkey")
		return nil
	end

	local window
	waitUntil(function()
		window = findKittyHotkey()
		return window ~= nil
	end, KITTY_LAUNCH_TIMEOUT)
	if window == nil then notify("kitty hotkey window did not appear") end

	return window
end

--- The screen OmniWM reveals scratchpads on: the one being interacted with.
local function interactionScreen()
	local display = query("displays", "--current", "--fields", "name").displays[1]
	for _, screen in ipairs(hs.screen.allScreens()) do
		if screen:name() == display.name then return screen end
	end

	return hs.mouse.getCurrentScreen()
end

--- A scratchpad keeps the size it had on another monitor; shrink and center it when it does not fit this one.
local function fitToScreen(window)
	local win = hs.window.get(window.windowId)
	if win == nil then return end

	local area = interactionScreen():frame()
	local frame = win:frame()
	if frame.w <= area.w and frame.h <= area.h then return end

	local width = round(area.w * KITTY_HOTKEY_FIT_RATIO)
	local height = round(area.h * KITTY_HOTKEY_FIT_RATIO)
	win:setFrame({ x = round(area.x + (area.w - width) / 2), y = round(area.y + (area.h - height) / 2), w = width, h = height })
end

--- Scratchpad toggle shows the window on the current monitor without focusing it.
local function revealKittyHotkey(window)
	omni("command", "scratchpad", "toggle", KITTY_HOTKEY_SCRATCHPAD)
	fitToScreen(window)
	focusWindowRobustly(window.id)
end

--- Floating drop-down terminal in a scratchpad slot: shown over the current workspace, parked off-screen otherwise.
local function toggleKittyHotkey()
	local window = findKittyHotkey() or launchKittyHotkey()
	if window == nil then return end

	if not window.isScratchpad then
		-- Slots only last for the OmniWM process; assigning floats and parks the focused window.
		focusWindowRobustly(window.id)
		omni("command", "scratchpad", "assign", KITTY_HOTKEY_SCRATCHPAD)
		revealKittyHotkey(window)
	elseif not window.isVisible then
		revealKittyHotkey(window)
	elseif window.isFocused then
		omni("command", "scratchpad", "toggle", KITTY_HOTKEY_SCRATCHPAD)
	elseif window.workspace.displayName == focusedWorkspace() then
		focusWindowRobustly(window.id)
	else
		-- Shown on another monitor: toggling summons it to this one.
		revealKittyHotkey(window)
	end
end

--- OmniWM has no size commands for floating windows: grow or shrink around the center, within the screen.
local function resizeFloating(window, axis, delta)
	local win = hs.window.get(window.windowId)
	if win == nil then return end

	local area = win:screen():frame()
	local frame = win:frame()
	local x, y, width, height = frame.x, frame.y, frame.w, frame.h
	if axis == "h" then
		local newWidth = clamp(width + delta, FLOATING_MIN_SIZE, area.w)
		x = clamp(x - (newWidth - width) / 2, area.x, area.x + area.w - newWidth)
		width = newWidth
	else
		local newHeight = clamp(height + delta, FLOATING_MIN_SIZE, area.h)
		y = clamp(y - (newHeight - height) / 2, area.y, area.y + area.h - newHeight)
		height = newHeight
	end

	win:setFrame({ x = round(x), y = round(y), w = round(width), h = round(height) })
end

--- Niri first, Dwindle as the fallback (a command for the other layout fails with layout_mismatch).
local function resizeFocused(axis, delta)
	local focused = queryWindows("--focused")[1]
	if focused ~= nil and focused.mode == "floating" then
		resizeFloating(focused, axis, delta)
		return
	end

	local amount = string.format("%+d", delta)
	local direction = delta > 0 and "grow" or "shrink"
	local niri = axis == "h" and { "set-container-primary-span", amount } or { "set-window-secondary-span", amount }
	local dwindle = { "resize", axis == "h" and "horizontal" or "vertical", direction }
	if not exec({ OMNIWMCTL, "command", table.unpack(niri) }, false) then exec({ OMNIWMCTL, "command", table.unpack(dwindle) }, false) end
end

--- Fullscreen for a floating window: fill its screen, then restore the previous frame.
local function toggleFloatingMaximize(window)
	local win = hs.window.get(window.windowId)
	if win == nil then return end

	local saved = maximized[window.windowId]
	if saved ~= nil then
		maximized[window.windowId] = nil
		win:setFrame(saved)
		return
	end

	local frame = win:frame()
	maximized[window.windowId] = { x = frame.x, y = frame.y, w = frame.w, h = frame.h }
	win:setFrame(win:screen():frame())
end

--- Layout commands act on the tiled window selected in the layout, so a focused floating window would be skipped.
local function layoutCommand(cmd, dir)
	local focused = queryWindows("--focused")[1]
	local floating = focused ~= nil and focused.mode == "floating"
	if cmd == "fullscreen" then
		if floating then
			toggleFloatingMaximize(focused)
		else
			exec({ OMNIWMCTL, "command", "toggle-fullscreen" }, false)
		end
		return
	end
	if floating then
		notify("Floating window: command only applies to tiled windows")
		return
	end

	local alternatives
	if cmd == "move" then
		alternatives = { { "move", dir } }
	elseif cmd == "move-column" then
		-- Up and down fall back to reordering inside the column.
		alternatives = { { "move-column", dir } }
		if dir == "up" then table.insert(alternatives, { "move-window-up" }) end
		if dir == "down" then table.insert(alternatives, { "move-window-down" }) end
	elseif cmd == "tabbed" then
		alternatives = { { "toggle-column-tabbed" } }
	else
		alternatives = { { "toggle-split" } }
	end
	for _, args in ipairs(alternatives) do
		if exec({ OMNIWMCTL, "command", table.unpack(args) }, false) then return end
	end
end

local function cycleAppWindow(direction)
	local bundleId = (query("active-workspace").focusedApp or {}).bundleId
	if bundleId == nil then
		notify("Oops, no focused window.")
		return
	end

	local ids = {}
	for _, window in ipairs(queryWindows("--bundle-id", bundleId)) do
		table.insert(ids, window.id)
	end
	if #ids < 2 then
		notify("There is only 1 window for this app.")
		return
	end

	focusWindowRobustly(nextId(ids, focusedWindowId(), direction))
end

local actions = {
	["app-toggle"] = function(params) toggleApp(params.app) end,
	["kitty-hotkey"] = function() toggleKittyHotkey() end,
	["cycle-app"] = function(params)
		if params.dir ~= "next" and params.dir ~= "prev" then return notify("wm: dir must be next or prev") end
		cycleAppWindow(params.dir)
	end,
	layout = function(params)
		local cmd, dir = params.cmd, params.dir
		local needsDirection = cmd == "move" or cmd == "move-column"
		if not (needsDirection or cmd == "fullscreen" or cmd == "tabbed" or cmd == "split") then return notify("wm: unknown layout cmd " .. tostring(cmd)) end
		if needsDirection and not DIRECTIONS[dir] then return notify("wm: layout " .. cmd .. " needs dir=left|right|up|down") end
		layoutCommand(cmd, dir)
	end,
	resize = function(params)
		local delta = math.tointeger(tonumber(params.delta))
		if (params.axis ~= "h" and params.axis ~= "v") or delta == nil then return notify("wm: resize needs axis=h|v and an integer delta") end
		resizeFocused(params.axis, delta)
	end,
}

function M.setup(route)
	hs.urlevent.bind(route, function(_, params)
		local action = actions[params.action]
		if action == nil then
			notify("wm: unknown action " .. tostring(params.action))
			return
		end

		local ok, err = pcall(action, params)
		if not ok then notify(tostring(err)) end
	end)
end

return M
