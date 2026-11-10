local M = {}

local config = {
	margins = {
		left = 8,
		bottom = 4,
		top = 4,
		right = 8,
	},
	moveStep = 40,
	minWidth = 480,
	minHeight = 240,
}

-- Last on-screen size per window id, as a share of the screen bounds. A window
-- summoned to another screen is scaled by it, so sizes survive screen changes.
local stashedSizes = {}

local function notify(message) hs.alert.show(message) end

local function copyFrame(frame)
	return {
		x = frame.x,
		y = frame.y,
		w = frame.w,
		h = frame.h,
	}
end

local function getFocusedWindow()
	local win = hs.window.focusedWindow()
	if win == nil then
		notify("No focused window")
		return nil
	end

	return win
end

local function getBounds(win)
	local screenFrame = win:screen():frame()
	local margins = config.margins

	return {
		x = screenFrame.x + margins.left,
		y = screenFrame.y + margins.top,
		w = screenFrame.w - margins.left - margins.right,
		h = screenFrame.h - margins.top - margins.bottom,
	}
end

local function fitDimension(value, minValue, maxValue) return math.min(math.max(value, minValue), maxValue) end

local function clampPosition(frame, bounds)
	local maxX = bounds.x + bounds.w - frame.w
	local maxY = bounds.y + bounds.h - frame.h

	frame.x = fitDimension(frame.x, bounds.x, maxX)
	frame.y = fitDimension(frame.y, bounds.y, maxY)

	return frame
end

local function clampFrame(frame, bounds)
	frame.w = fitDimension(frame.w, config.minWidth, bounds.w)
	frame.h = fitDimension(frame.h, config.minHeight, bounds.h)

	return clampPosition(frame, bounds)
end

local function centerFrame(frame, bounds)
	frame.x = bounds.x + math.floor((bounds.w - frame.w) / 2)
	frame.y = bounds.y + math.floor((bounds.h - frame.h) / 2)

	return frame
end

local function centerWindow(win)
	local bounds = getBounds(win)
	local frame = copyFrame(win:frame())
	local share = stashedSizes[win:id()]
	if share ~= nil then
		frame.w = math.floor(share.w * bounds.w)
		frame.h = math.floor(share.h * bounds.h)
	end
	win:setFrame(centerFrame(clampFrame(frame, bounds), bounds))
end

-- Call before the window leaves its screen. A window that is hidden or off
-- screen has no meaningful size, so keep the previous one.
local function stashSize(win)
	local frame = win:frame()
	local cx, cy = frame.x + frame.w / 2, frame.y + frame.h / 2
	for _, screen in ipairs(hs.screen.allScreens()) do
		local f = screen:fullFrame()
		if cx >= f.x and cx < f.x + f.w and cy >= f.y and cy < f.y + f.h then
			local bounds = getBounds(win)
			stashedSizes[win:id()] = { w = frame.w / bounds.w, h = frame.h / bounds.h }
			return
		end
	end
end

local function moveWindow(win, axis, size)
	local bounds = getBounds(win)
	local frame = clampFrame(copyFrame(win:frame()), bounds)
	local appliedSize = size * 2

	if axis == "h" then
		frame.x = frame.x + appliedSize
	elseif axis == "v" then
		frame.y = frame.y + appliedSize
	else
		notify("Unknown move axis")
		return
	end

	win:setFrame(clampPosition(frame, bounds))
end

local function resizeWindow(win, axis, size)
	local bounds = getBounds(win)
	local currentFrame = clampFrame(copyFrame(win:frame()), bounds)
	local frame = copyFrame(currentFrame)
	local dw = 0
	local dh = 0
	local appliedSize = size * 2

	if axis == "width" then
		dw = appliedSize
	elseif axis == "height" then
		dh = appliedSize
	elseif axis == "both" then
		dw = appliedSize
		dh = appliedSize
	else
		notify("Unknown resize axis")
		return
	end

	local centerX = currentFrame.x + (currentFrame.w / 2)
	local centerY = currentFrame.y + (currentFrame.h / 2)

	frame.w = frame.w + dw
	frame.h = frame.h + dh
	frame.w = fitDimension(frame.w, config.minWidth, bounds.w)
	frame.h = fitDimension(frame.h, config.minHeight, bounds.h)
	frame.x = math.floor(centerX - (frame.w / 2))
	frame.y = math.floor(centerY - (frame.h / 2))

	win:setFrame(clampPosition(frame, bounds))
end

local function handleRoute(_, params)
	local action = params["action"]
	local target = params["target"]

	if action == nil then
		notify("Missing action")
		return
	end

	-- An explicit window id avoids racing the focus change that precedes the call.
	local win = params["window"] and hs.window.get(tonumber(params["window"])) or getFocusedWindow()
	if win == nil then return end

	if action == "stash" then
		stashSize(win)
		return
	end

	if action == "move" then
		if target == "center" then
			centerWindow(win)
			return
		end

		local axis = params["axis"]
		local size = tonumber(params["size"])

		if axis == nil then
			notify("Missing move axis")
			return
		end
		if size == nil then
			notify("Invalid move size")
			return
		end
		moveWindow(win, axis, size)
		return
	end

	if action == "resize" then
		local axis = params["axis"]
		local size = tonumber(params["size"])

		if axis == nil then
			notify("Missing resize axis")
			return
		end
		if size == nil then
			notify("Invalid resize size")
			return
		end
		resizeWindow(win, axis, size)
		return
	end

	notify("Unknown action")
end

function M.setup(route) hs.urlevent.bind(route, handleRoute) end

return M
