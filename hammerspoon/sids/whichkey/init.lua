-- Delayed key guide for modal shortcuts, driven over URL routes:
--   whichkey?action=show&group=<id>   show after a short delay (replaces the visible guide)
--   whichkey?action=hide[&group=<id>] cancel the pending guide / hide it (only if it is <id>, when given)
-- Groups are generated from goku/menus.toml (see groups.lua).
local ui = require("sids.whichkey.ui")
local groups = require("sids.whichkey.groups")

local M = {}

local showDelaySeconds = 0.45
local maxVisibleSeconds = 12 -- safety net if a hide never arrives

local state = {
	canvas = nil,
	showTimer = nil,
	expireTimer = nil,
	pendingGroup = nil,
	visibleGroup = nil,
}

local function stopTimer(name)
	if state[name] ~= nil then
		state[name]:stop()
		state[name] = nil
	end
end

local function hideCanvas()
	stopTimer("expireTimer")
	state.visibleGroup = nil
	if state.canvas ~= nil then state.canvas:hide() end
end

local function render(groupName)
	local group = groups[groupName]
	if group == nil then
		hs.alert.show("WhichKey: unknown group " .. tostring(groupName))
		return
	end

	local window = hs.window.focusedWindow()
	local screen = window and window:screen() or hs.mouse.getCurrentScreen() or hs.screen.mainScreen()
	local frame, elements = ui.build(group, screen:frame())

	if state.canvas == nil then
		state.canvas = hs.canvas.new(frame)
		state.canvas:behavior(hs.canvas.windowBehaviors.canJoinAllSpaces)
		state.canvas:level(hs.canvas.windowLevels.floating)
	end
	state.canvas:frame(frame)
	state.canvas:replaceElements(table.unpack(elements))
	if state.visibleGroup == nil then state.canvas:show(0.08) end

	state.visibleGroup = groupName
	stopTimer("expireTimer")
	state.expireTimer = hs.timer.doAfter(maxVisibleSeconds, hideCanvas)
end

local function show(groupName)
	stopTimer("showTimer")
	if state.visibleGroup ~= nil then
		state.pendingGroup = nil
		render(groupName)
		return
	end

	state.pendingGroup = groupName
	state.showTimer = hs.timer.doAfter(showDelaySeconds, function()
		state.showTimer, state.pendingGroup = nil, nil
		render(groupName)
	end)
end

local function hide(groupName)
	if groupName == nil or state.pendingGroup == groupName then
		stopTimer("showTimer")
		state.pendingGroup = nil
	end
	if groupName == nil or state.visibleGroup == groupName then hideCanvas() end
end

--- Render a group to a PNG without showing it (development aid).
function M.snapshot(groupName, path)
	local frame, elements = ui.build(groups[groupName], hs.screen.mainScreen():frame())
	local canvas = hs.canvas.new({ x = 0, y = 0, w = frame.w, h = frame.h })
	canvas:replaceElements(table.unpack(elements))
	local image = canvas:imageFromCanvas()
	canvas:delete()
	return image:saveToFile(path)
end

function M.setup(route)
	hs.urlevent.bind(route, function(_, params)
		local action = params["action"]
		if action == "show" and params["group"] ~= nil then
			show(params["group"])
		elseif action == "hide" then
			hide(params["group"])
		end
	end)
end

return M
