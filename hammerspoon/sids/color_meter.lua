local M = {}

local state = {
	selectionRect = nil,
	canvas = nil,
	mouseDownTap = nil,
	mouseDragTap = nil,
	mouseUpTap = nil,
	hotkey = nil,
}

local overlayColor = { red = 1, alpha = 0.5 }
local markerColor = { red = 1, green = 0, blue = 0, alpha = 0.5 }
local tolerance = 0.05

local function ensureCanvas()
	if state.canvas == nil then
		state.canvas = hs.canvas.new({ x = 0, y = 0, w = 0, h = 0 })
	end

	return state.canvas
end

local function hideCanvas()
	if state.canvas ~= nil then state.canvas:hide() end
end

local function stopSelectionTaps()
	local taps = { state.mouseDownTap, state.mouseDragTap, state.mouseUpTap }
	for _, tap in ipairs(taps) do
		if tap ~= nil then tap:stop() end
	end

	state.mouseDownTap = nil
	state.mouseDragTap = nil
	state.mouseUpTap = nil
end

local function normalizedRect(rect)
	local x = math.min(rect.x, rect.x + rect.w)
	local y = math.min(rect.y, rect.y + rect.h)
	local w = math.abs(rect.w)
	local h = math.abs(rect.h)

	return hs.geometry.rect(x, y, w, h)
end

local function updateSelectionOverlay(rect)
	local canvas = ensureCanvas()
	local frame = normalizedRect(rect)

	canvas:frame(frame)
	canvas:replaceElements({
		{
			type = "rectangle",
			action = "stroke",
			frame = { x = 0, y = 0, w = frame.w, h = frame.h },
			strokeColor = overlayColor,
			strokeWidth = 2,
		},
	})
	canvas:show()
end

local function rgbKey(color)
	return string.format("%.2f,%.2f,%.2f", color.red, color.green, color.blue)
end

local function parseRgbKey(key)
	local rgb = {}
	for value in key:gmatch("[^,]+") do
		rgb[#rgb + 1] = tonumber(value)
	end
	return rgb
end

local function colorsMatch(color, rgb)
	return math.abs(color.red - rgb[1]) < tolerance
		and math.abs(color.green - rgb[2]) < tolerance
		and math.abs(color.blue - rgb[3]) < tolerance
end

local function markLeastCommonColor(image, rect)
	local colors = {}
	local leastColor = nil
	local leastCount = math.huge

	for x = 0, rect.w - 1 do
		for y = 0, rect.h - 1 do
			local color = image:colorAt({ x = x, y = y })
			if color ~= nil and (color.red > tolerance or color.green > tolerance or color.blue > tolerance) then
				local key = rgbKey(color)
				colors[key] = (colors[key] or 0) + 1
			end
		end
	end

	for colorKey, count in pairs(colors) do
		if count < leastCount then
			leastColor = colorKey
			leastCount = count
		end
	end

	if leastColor == nil then return end

	local rgb = parseRgbKey(leastColor)
	local canvas = ensureCanvas()
	canvas:frame(rect)
	canvas:replaceElements({})

	for x = 0, rect.w - 1 do
		for y = 0, rect.h - 1 do
			local color = image:colorAt({ x = x, y = y })
			if color ~= nil and colorsMatch(color, rgb) then
				canvas:appendElements({
					type = "rectangle",
					action = "fill",
					frame = { x = x, y = y, w = 1, h = 1 },
					fillColor = markerColor,
				})
			end
		end
	end

	canvas:show()
	hs.timer.doAfter(3, hideCanvas)
end

local function analyzeSelection()
	local rect = normalizedRect(state.selectionRect)
	if rect.w < 1 or rect.h < 1 then
		hideCanvas()
		return
	end

	local image = hs.screen.mainScreen():snapshot(rect)
	if image == nil then
		hideCanvas()
		return
	end

	markLeastCommonColor(image, rect)
end

local function beginSelection()
	stopSelectionTaps()
	state.selectionRect = hs.geometry.rect(hs.mouse.absolutePosition(), { w = 0, h = 0 })

	state.mouseDownTap = hs.eventtap.new({ hs.eventtap.event.types.leftMouseDown }, function()
		local pos = hs.mouse.absolutePosition()
		state.selectionRect.x = pos.x
		state.selectionRect.y = pos.y
		state.selectionRect.w = 0
		state.selectionRect.h = 0
		updateSelectionOverlay(state.selectionRect)
		return true
	end)

	state.mouseDragTap = hs.eventtap.new({ hs.eventtap.event.types.leftMouseDragged }, function()
		local pos = hs.mouse.absolutePosition()
		state.selectionRect.w = pos.x - state.selectionRect.x
		state.selectionRect.h = pos.y - state.selectionRect.y
		updateSelectionOverlay(state.selectionRect)
		return true
	end)

	state.mouseUpTap = hs.eventtap.new({ hs.eventtap.event.types.leftMouseUp }, function()
		stopSelectionTaps()
		analyzeSelection()
		return true
	end)

	state.mouseDownTap:start()
	state.mouseDragTap:start()
	state.mouseUpTap:start()
end

function M.setup()
	if state.hotkey ~= nil then return end

	state.hotkey = hs.hotkey.bind({ "cmd", "shift" }, "c", beginSelection)
end

return M
