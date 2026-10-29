local M = {}

local OMNIWMCTL = "/opt/homebrew/bin/omniwmctl"
local maxHints = 9
local borderWidth = 6
local routeCanvases = {}
local routeTargets = {}
local keyWatcher = nil
local dismissTimer = nil
local profileState = nil

local hintKeys = { "1", "2", "3", "4", "5", "6", "7", "8", "9" }

local colors = {
	border = { hex = "#d20f39", alpha = 0.92 },
	number = { hex = "#d20f39", alpha = 0.84 },
}

local function notify(message) hs.alert.show(message) end

local function writeProfile(event, detail)
	if profileState == nil then return end

	local now = hs.timer.secondsSinceEpoch()
	local file = io.open(profileState.path, "a")
	if file ~= nil then
		file:write(string.format(
			"%s\t%.6f\t%.2f\t%.2f\t%s\n",
			event,
			now,
			(now - profileState.start) * 1000,
			(now - profileState.last) * 1000,
			detail or ""
		))
		file:close()
	end
end

local function startProfile(enabled)
	if not enabled then
		profileState = nil
		return
	end

	hs.execute("/bin/mkdir -p /tmp/aswindowhints-real-profile", true)
	local now = hs.timer.secondsSinceEpoch()
	profileState = {
		start = now,
		last = now,
		path = "/tmp/aswindowhints-real-profile/hs-profile.tsv",
	}

	local file = io.open(profileState.path, "w")
	if file ~= nil then
		file:write("event\tabs_time\ttotal_ms\tdelta_ms\tdetail\n")
		file:close()
	end
	writeProfile("start", "")
	print("aswindowhints profile start")
end

local function markProfile(name, detail)
	if profileState == nil then return end

	local now = hs.timer.secondsSinceEpoch()
	print(string.format(
		"aswindowhints %-24s %+8.2f ms total %+8.2f ms %s",
		name,
		(now - profileState.last) * 1000,
		(now - profileState.start) * 1000,
		detail or ""
	))
	writeProfile(name, detail)
	profileState.last = now
end

local function omniQuery(args)
	local output, ok, _, rc = hs.execute(OMNIWMCTL .. " query " .. table.concat(args, " ") .. " --format json", false)
	if not ok then return nil, "omniwmctl failed (" .. tostring(rc) .. "): " .. tostring(output) end

	local decoded = hs.json.decode(output)
	if decoded == nil or decoded.result == nil then return nil, "omniwmctl returned no result: " .. tostring(output) end

	return decoded.result.payload, nil
end

local function focusedWorkspaceWindowIds()
	local active, err = omniQuery({ "active-workspace" })
	if active == nil then return nil, err end

	local payload, windowsErr = omniQuery({ "windows", "--workspace", active.workspace.rawName, "--visible", "--fields", "window-id" })
	if payload == nil then return nil, windowsErr end
	markProfile("omniwm ids")

	local ids = {}
	for _, window in ipairs(payload.windows) do
		if window.windowId ~= nil then table.insert(ids, window.windowId) end
		if #ids >= maxHints then break end
	end
	markProfile("parse ids")

	return ids, nil
end

local function targetForWindowId(windowId)
	local started = hs.timer.secondsSinceEpoch()
	local win = hs.window.get(windowId)
	markProfile("hs.window.get", string.format("id=%s elapsed_ms=%.2f", tostring(windowId), (hs.timer.secondsSinceEpoch() - started) * 1000))
	if win == nil or win:screen() == nil then return nil end

	local frameStarted = hs.timer.secondsSinceEpoch()
	local frame = win:frame()
	markProfile("frame", string.format("id=%s elapsed_ms=%.2f", tostring(windowId), (hs.timer.secondsSinceEpoch() - frameStarted) * 1000))

	return {
		windowId = windowId,
		win = win,
		frame = frame,
		appName = (win:application() and win:application():name()) or "",
	}
end

local function focusedWorkspaceTargets()
	local ids, err = focusedWorkspaceWindowIds()
	if ids == nil then return nil, err end

	local targets = {}
	local seen = {}
	for _, id in ipairs(ids) do
		local target = targetForWindowId(id)
		local hsId = target and target.win:id()
		if target ~= nil and hsId ~= nil and seen[hsId] ~= true then
			table.insert(targets, target)
			seen[hsId] = true
		end
	end
	markProfile("resolve targets")

	return targets, nil
end

local function clear()
	if dismissTimer ~= nil then
		dismissTimer:stop()
		dismissTimer = nil
	end

	if keyWatcher ~= nil then
		keyWatcher:stop()
		keyWatcher = nil
	end

	for _, canvas in ipairs(routeCanvases) do
		canvas:delete()
	end

	routeCanvases = {}
	routeTargets = {}
end

local function badgeSizeFor(frame)
	local minSide = math.min(frame.w, frame.h)
	return math.floor(math.max(96, math.min(220, minSide * 0.35)))
end

local function configureCanvas(canvas)
	canvas:level(hs.canvas.windowLevels.overlay)
	canvas:behavior({
		hs.canvas.windowBehaviors.canJoinAllSpaces,
		hs.canvas.windowBehaviors.fullScreenAuxiliary,
	})
	canvas:clickActivating(false)
	return canvas
end

local function showCanvas(rect, elements)
	local canvas = configureCanvas(hs.canvas.new(rect))
	canvas:appendElements(elements)
	canvas:show()
	table.insert(routeCanvases, canvas)
end

local function drawOverlay(target, index)
	local drawStarted = hs.timer.secondsSinceEpoch()
	local frame = target.frame or target.win:frame()
	if frame.w <= 0 or frame.h <= 0 then return false end
	if frame.w <= borderWidth * 2 or frame.h <= borderWidth * 2 then return false end

	local badgeSize = badgeSizeFor(frame)
	local textSize = math.floor(badgeSize * 0.72)
	local textHeight = textSize * 1.25
	local bw = borderWidth
	local borderElement = {
		type = "rectangle",
		action = "fill",
		fillColor = colors.border,
		frame = { x = 0, y = 0, w = "100%", h = "100%" },
	}

	showCanvas({ x = frame.x, y = frame.y, w = frame.w, h = bw }, { borderElement })
	showCanvas({ x = frame.x, y = frame.y + frame.h - bw, w = frame.w, h = bw }, { borderElement })
	showCanvas({ x = frame.x, y = frame.y, w = bw, h = frame.h }, { borderElement })
	showCanvas({ x = frame.x + frame.w - bw, y = frame.y, w = bw, h = frame.h }, { borderElement })

	showCanvas({
		x = frame.x + (frame.w - badgeSize) / 2,
		y = frame.y + (frame.h - badgeSize) / 2,
		w = badgeSize,
		h = badgeSize,
	}, {
		{
			type = "text",
			text = tostring(index),
			textFont = "Helvetica-Bold",
			textSize = textSize,
			textColor = colors.number,
			textAlignment = "center",
			frame = {
				x = 0,
				y = math.max(0, (badgeSize - textHeight) / 2),
				w = badgeSize,
				h = textHeight,
			},
		},
	})

	markProfile("draw target", string.format("index=%d elapsed_ms=%.2f", index, (hs.timer.secondsSinceEpoch() - drawStarted) * 1000))
	return true
end

local function focusTarget(index)
	local target = routeTargets[index]
	if target == nil then return end

	clear()
	target.win:focus()
end

local function keyCodeFor(key)
	return hs.keycodes.map[key]
end

local function startKeyWatcher()
	keyWatcher = hs.eventtap.new({ hs.eventtap.event.types.keyDown }, function(event)
		local code = event:getKeyCode()

		if code == keyCodeFor("escape") then
			clear()
			return true
		end

		for index, key in ipairs(hintKeys) do
			if code == keyCodeFor(key) then
				focusTarget(index)
				return true
			end
		end

		return true
	end)

	keyWatcher:start()
	dismissTimer = hs.timer.doAfter(10, clear)
end

function M.show(options)
	options = options or {}
	startProfile(options.profile == true)
	clear()
	markProfile("clear")

	local targets, err = focusedWorkspaceTargets()
	if targets == nil then
		notify(err)
		return
	end
	if #targets == 0 then
		notify("No windows in the active workspace")
		return
	end

	routeTargets = {}
	for _, target in ipairs(targets) do
		local index = #routeTargets + 1
		if drawOverlay(target, index) then table.insert(routeTargets, target) end
	end
	markProfile("draw overlays")

	if #routeTargets == 0 then
		clear()
		notify("No drawable windows in the active workspace")
		return
	end

	startKeyWatcher()
	markProfile("eventtap")
end

function M.setup(route)
	hs.urlevent.bind(route, function(_, params) M.show({ profile = params["profile"] == "1" }) end)
end

return M
