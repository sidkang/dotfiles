local M = {}

local showDelaySeconds = 0.45

local latte = {
	rosewater = { hex = "#dc8a78" },
	flamingo = { hex = "#dd7878" },
	pink = { hex = "#ea76cb" },
	mauve = { hex = "#8839ef" },
	red = { hex = "#d20f39" },
	maroon = { hex = "#e64553" },
	peach = { hex = "#fe640b" },
	yellow = { hex = "#df8e1d" },
	green = { hex = "#40a02b" },
	teal = { hex = "#179299" },
	sky = { hex = "#04a5e5" },
	sapphire = { hex = "#209fb5" },
	blue = { hex = "#1e66f5" },
	lavender = { hex = "#7287fd" },
	text = { hex = "#4c4f69" },
	subtext1 = { hex = "#5c5f77" },
	subtext0 = { hex = "#6c6f85" },
	overlay2 = { hex = "#7c7f93" },
	overlay1 = { hex = "#8c8fa1" },
	overlay0 = { hex = "#9ca0b0" },
	surface2 = { hex = "#acb0be" },
	surface1 = { hex = "#bcc0cc" },
	surface0 = { hex = "#ccd0da" },
	base = { hex = "#eff1f5" },
	mantle = { hex = "#e6e9ef" },
	crust = { hex = "#dce0e8" },
}

local function color(name, alpha)
	local baseColor = latte[name] or latte.peach
	local resolved = { hex = baseColor.hex }

	if alpha ~= nil then resolved.alpha = alpha end

	return resolved
end

local theme = {
	card = color("base", 0.92),
	cardBorder = color("surface1", 0.92),
	divider = color("surface1", 1),
	title = color("text", 1),
	subtitle = color("overlay1", 1),
	desc = color("subtext0", 1),
	pillBg = color("green", 0.10),
	pillBorder = color("teal", 0.36),
	pillText = color("text", 1),
}

local layout = {
	minWidth = 196,
	maxWidth = 420,
	padding = 14,
	cornerRadius = 18,
	titleHeight = 24,
	subtitleHeight = 14,
	dividerGap = 14,
	rowHeight = 38,
	rowGap = 8,
	pillMinWidth = 38,
	pillMaxWidth = 108,
	pillHeight = 24,
	pillRadius = 12,
	pillToTextGap = 17,
	segmentGap = 0,
	pillTextHeight = 19,
	lineTextHeight = 18,
	bottomMargin = 28,
	rightMargin = 28,
	minHeight = 140,
}

local groups = {
	["aerospace-mode"] = {
		desc = "AeroSpace Mode",
		items = {
			{ key = "R", desc = "{Send|blue} Mode" },
			{ key = "T", desc = "{Toggle|blue}" },
			{ key = "F", desc = "{Open|blue} Mode" },
			{ key = "G", desc = "{Go|blue} Mode" },
			{ key = "S", desc = "{Swap|peach} Mode" },
			{ key = "Z", desc = "进入 {Z Mode|teal}" },
			{ key = "V", desc = "{Close|mauve} App" },
			{ key = "HJKL", desc = "切换关注" },
			{ key = "Shift+HJKL", desc = "移动窗口" },
			{ key = "Ctrl+HJKL", desc = "合并窗口" },
			{ key = "1-6/QWE", desc = "切换工作区" },
		},
	},
	["as-send-ws"] = {
		desc = "AeroSpace Send",
		items = {
			{ key = "1-5", desc = "发送到工作区 {1-5|teal}" },
			{ key = "Q/W/E", desc = "发送到工作区 {Q/W/E|blue}" },
			{ key = "A/S/D", desc = "发送到工作区 {A/S/D|mauve}" },
			{ key = "Caps", desc = "退出" },
		},
	},
	["as-toggle"] = {
		desc = "AeroSpace Toggle",
		items = {
			{ key = "J", desc = "布局切换 {tiles <-> accordion|teal}" },
			{ key = "K", desc = "布局切换 {horizontal <-> vertical|blue}" },
			{ key = "F", desc = "布局切换 {floating <-> tiling|mauve}" },
			{ key = "E", desc = "重启 {AeroSpace borders|red}" },
			{ key = "B", desc = "平衡 {window sizes|green}" },
			{ key = "R", desc = "重载 {AeroSpace config|yellow}" },
			{ key = "G", desc = "移动 {ghost window|sky}" },
			{ key = "C", desc = "居中 {floating window|peach}" },
		},
	},
	["as-open"] = {
		desc = "App Toggle",
		items = {
			{ key = "F", desc = "打开 {Finder|blue}" },
			{ key = "W", desc = "打开 {WeChat|green}" },
			{ key = "T", desc = "打开 {Telegram|teal}" },
			{ key = "G", desc = "打开 {Google Chrome|peach}" },
		},
	},
	["as-go"] = {
		desc = "AeroSpace Go",
		items = {
			{ key = "1", desc = "切到工作区 {1|teal}" },
			{ key = "2", desc = "切到工作区 {2|blue}" },
			{ key = "3", desc = "切到工作区 {3|mauve}" },
			{ key = "4", desc = "切到工作区 {4|green}" },
			{ key = "5", desc = "切到工作区 {5|peach}" },
			{ key = "Q", desc = "切到工作区 {Q|red}" },
			{ key = "W", desc = "切到工作区 {W|yellow}" },
			{ key = "E", desc = "切到工作区 {E|sky}" },
			{ key = "A", desc = "切到工作区 {A|teal}" },
			{ key = "S", desc = "切到工作区 {S|blue}" },
			{ key = "D", desc = "切到工作区 {D|mauve}" },
			{ key = "T", desc = "切到工作区 {T|green}" },
		},
	},
	["as-swap"] = {
		desc = "AeroSpace Swap",
		items = {
			{ key = "H", desc = "交换到{左侧|teal}" },
			{ key = "J", desc = "交换到{下方|green}" },
			{ key = "K", desc = "交换到{上方|mauve}" },
			{ key = "L", desc = "交换到{右侧|blue}" },
		},
	},
	["m1ddc-pbp"] = {
		desc = "Display PBP",
		items = {
			{ key = "1", desc = "主输入切到 {USB-C|teal}" },
			{ key = "2", desc = "主输入切到 {DP|blue}" },
			{ key = "3", desc = "主输入切到 {HDMI|mauve}" },
			{ key = "Q", desc = "PBP 输入设为 {USB-C|green}" },
			{ key = "W", desc = "PBP 输入设为 {DP|yellow}" },
			{ key = "E", desc = "PBP 输入设为 {HDMI|sky}" },
			{ key = "A", desc = "PBP {off|red}" },
			{ key = "S", desc = "PBP {small|peach}" },
			{ key = "D", desc = "PBP {large|teal}" },
			{ key = "F", desc = "PBP {50:50|blue}" },
		},
	},
	["z-mode"] = {
		desc = "Z Mode",
		items = {
			{ key = "1", desc = "显示器输入切到 {USB-C|teal}" },
			{ key = "2", desc = "显示器输入切到 {DP|blue}" },
			{ key = "3", desc = "显示器输入切到 {HDMI|mauve}" },
			{ key = "Q", desc = "进入 {Display PBP|green}" },
			{ key = "O", desc = "{Bob|blue} 划词翻译" },
			{ key = "P", desc = "{Bob|teal} 截图翻译" },
			{ key = "9", desc = "打开 {Hammerspoon Console|peach}" },
			{ key = "0", desc = "重载 {Hammerspoon Config|red}" },
			{ key = "=", desc = "发送 {Error Notify|yellow}" },
			{ key = "/", desc = "触发 {Xnip Capture|sky}" },
		},
	},
}

local state = {
	canvas = nil,
	measureCanvas = nil,
	showTimer = nil,
	pendingGroupName = nil,
	visibleGroupName = nil,
}

local measureTextElement = {
	type = "text",
	textSize = 14,
	frame = { x = 0, y = 0, w = 10, h = 18 },
}

local function notifyMissingGroup(groupName)
	hs.notify
		.new({
			title = "WhichKey",
			informativeText = string.format("group not found: %s", groupName or "nil"),
		})
		:send()
end

local function getGroup(groupName) return groupName and groups[groupName] or nil end

local function parseSegments(text)
	local segments = {}
	local cursor = 1

	while cursor <= #text do
		local startPos, endPos, token = text:find("{(.-)}", cursor)

		if startPos == nil then
			local plainText = text:sub(cursor)
			if plainText ~= "" then segments[#segments + 1] = { text = plainText, color = theme.desc } end
			break
		end

		if startPos > cursor then segments[#segments + 1] = {
			text = text:sub(cursor, startPos - 1),
			color = theme.desc,
		} end

		local content, colorKey = token:match("^(.-)|([%a_]+)$")
		segments[#segments + 1] = {
			text = content or token,
			color = color(colorKey or "peach", 1),
		}

		cursor = endPos + 1
	end

	return segments
end

local function ensureMeasureCanvas()
	if state.measureCanvas == nil then
		state.measureCanvas = hs.canvas.new({ x = 0, y = 0, w = 10, h = 10 })
		state.measureCanvas:appendElements(measureTextElement)
	end

	return state.measureCanvas
end

local function measureTextWidth(text)
	local canvas = ensureMeasureCanvas()
	local size = canvas:minimumTextSize(1, text)

	return math.ceil(size.w)
end

local function measureSegmentsWidth(segments)
	local width = 0

	for index, segment in ipairs(segments) do
		width = width + measureTextWidth(segment.text)
		if index < #segments then width = width + layout.segmentGap end
	end

	return width
end

local function getPillWidth(group)
	local maxKeyWidth = 0

	for _, item in ipairs(group.items) do
		maxKeyWidth = math.max(maxKeyWidth, measureTextWidth(item.key or ""))
	end

	local width = maxKeyWidth + 18
	return math.max(layout.pillMinWidth, math.min(width, layout.pillMaxWidth))
end

local function getPanelHeight(itemCount)
	local contentRows = math.max(itemCount, 1)
	local rowsHeight = (contentRows * layout.rowHeight) + ((contentRows - 1) * layout.rowGap)
	local height = layout.padding
		+ layout.titleHeight
		+ layout.subtitleHeight
		+ layout.dividerGap
		+ 10
		+ rowsHeight
		+ layout.padding

	return math.max(height, layout.minHeight)
end

local function getPanelWidth(group)
	local maxTextWidth = 0
	local titleWidth = measureTextWidth(group.desc)
	local pillWidth = getPillWidth(group)

	for _, item in ipairs(group.items) do
		maxTextWidth = math.max(maxTextWidth, measureSegmentsWidth(parseSegments(item.desc)))
	end

	local contentWidth = pillWidth + layout.pillToTextGap + maxTextWidth
	local headerWidth = titleWidth + 6
	local bodyWidth = contentWidth + 2
	local width = (layout.padding * 2) + math.max(headerWidth, bodyWidth)

	return math.max(layout.minWidth, math.min(width, layout.maxWidth))
end

local function getPanelFrame(group)
	local focusedWindow = hs.window.focusedWindow()
	local screen = focusedWindow and focusedWindow:screen() or hs.screen.mainScreen()
	local screenFrame = screen:frame()
	local width = getPanelWidth(group)
	local height = getPanelHeight(#group.items)

	return {
		x = screenFrame.x + screenFrame.w - width - layout.rightMargin,
		y = screenFrame.y + screenFrame.h - height - layout.bottomMargin,
		w = width,
		h = height,
	}
end

local function appendRowElements(elements, item, index, frame, pillWidth)
	local top = layout.padding + layout.titleHeight + layout.subtitleHeight + layout.dividerGap + 10
	local rowY = top + ((index - 1) * (layout.rowHeight + layout.rowGap))
	local rowX = layout.padding
	local rowCenterY = rowY + (layout.rowHeight / 2)
	local pillY = rowCenterY - (layout.pillHeight / 2)
	local textX = rowX + pillWidth + layout.pillToTextGap
	local textY = rowCenterY - (layout.lineTextHeight / 2)
	local pillTextY = rowCenterY - (layout.pillTextHeight / 2)
	local segments = parseSegments(item.desc)

	elements[#elements + 1] = {
		type = "rectangle",
		action = "fill",
		roundedRectRadii = { xRadius = layout.pillRadius, yRadius = layout.pillRadius },
		fillColor = theme.pillBg,
		frame = { x = rowX, y = pillY, w = pillWidth, h = layout.pillHeight },
	}

	elements[#elements + 1] = {
		type = "rectangle",
		action = "stroke",
		strokeWidth = 1,
		roundedRectRadii = { xRadius = layout.pillRadius, yRadius = layout.pillRadius },
		strokeColor = theme.pillBorder,
		frame = { x = rowX, y = pillY, w = pillWidth, h = layout.pillHeight },
	}

	elements[#elements + 1] = {
		type = "text",
		text = item.key,
		textSize = 16,
		textColor = theme.pillText,
		textAlignment = "center",
		frame = { x = rowX, y = pillTextY, w = pillWidth, h = layout.pillTextHeight },
	}

	-- Render each desc segment as its own text element so accent text can appear
	-- anywhere in the sentence while staying on the same baseline as the prefix.
	for segmentIndex, segment in ipairs(segments) do
		local segmentWidth = measureTextWidth(segment.text)

		elements[#elements + 1] = {
			type = "text",
			text = segment.text,
			textSize = 14,
			textColor = segment.color,
			frame = { x = textX, y = textY, w = segmentWidth + 2, h = layout.lineTextHeight },
		}

		textX = textX + segmentWidth
		if segmentIndex < #segments then textX = textX + layout.segmentGap end
	end
end

local function buildElements(group, frame)
	local elements = {}
	local pillWidth = getPillWidth(group)

	-- Keep the card structure crisp and symmetrical. A stronger border and row
	-- organization read more naturally here than a fake drop shadow in canvas.
	elements[#elements + 1] = {
		type = "rectangle",
		action = "fill",
		roundedRectRadii = { xRadius = layout.cornerRadius, yRadius = layout.cornerRadius },
		fillColor = theme.card,
		frame = { x = 0, y = 0, w = frame.w, h = frame.h },
	}

	elements[#elements + 1] = {
		type = "rectangle",
		action = "stroke",
		strokeWidth = 1,
		roundedRectRadii = { xRadius = layout.cornerRadius, yRadius = layout.cornerRadius },
		strokeColor = theme.cardBorder,
		frame = { x = 0.5, y = 0.5, w = frame.w - 1, h = frame.h - 1 },
	}

	elements[#elements + 1] = {
		type = "text",
		text = "KEY GUIDE",
		textSize = 10,
		textColor = theme.subtitle,
		frame = { x = layout.padding, y = layout.padding - 1, w = frame.w - (layout.padding * 2), h = 14 },
	}

	elements[#elements + 1] = {
		type = "text",
		text = group.desc,
		textSize = 19,
		textColor = theme.title,
		frame = { x = layout.padding, y = layout.padding + 12, w = frame.w - (layout.padding * 2), h = 26 },
	}

	elements[#elements + 1] = {
		type = "segments",
		action = "stroke",
		strokeColor = theme.divider,
		strokeWidth = 1,
		coordinates = {
			{ x = layout.padding, y = layout.padding + layout.titleHeight + layout.subtitleHeight + 12 },
			{ x = frame.w - layout.padding, y = layout.padding + layout.titleHeight + layout.subtitleHeight + 12 },
		},
	}

	-- Build each row from simple primitives so the module stays self-contained and
	-- easy to tweak without introducing helpers from elsewhere in the config.
	for index, item in ipairs(group.items) do
		appendRowElements(elements, item, index, frame, pillWidth)
	end

	return elements
end

local function ensureCanvas(frame)
	if state.canvas == nil then
		state.canvas = hs.canvas.new(frame)
		state.canvas:behavior(hs.canvas.windowBehaviors.canJoinAllSpaces)
		state.canvas:level(hs.canvas.windowLevels.floating)
	else
		state.canvas:frame(frame)
	end

	return state.canvas
end

local function cancelPendingShow()
	if state.showTimer ~= nil then
		state.showTimer:stop()
		state.showTimer = nil
	end
end

local function renderShow(groupName)
	local group = getGroup(groupName)

	if group == nil then
		notifyMissingGroup(groupName)
		return
	end

	local frame = getPanelFrame(group)
	local canvas = ensureCanvas(frame)
	local elements = buildElements(group, frame)

	canvas:replaceElements(table.unpack(elements))
	canvas:show()
	canvas:alpha(1)
	canvas:topLeft({ x = frame.x, y = frame.y })
	canvas:size({ w = frame.w, h = frame.h })
	state.visibleGroupName = groupName
end

local function show(groupName)
	cancelPendingShow()
	if state.visibleGroupName ~= nil then
		renderShow(groupName)
		return
	end

	state.pendingGroupName = groupName
	state.showTimer = hs.timer.doAfter(showDelaySeconds, function()
		if state.pendingGroupName ~= groupName then return end
		state.showTimer = nil
		state.pendingGroupName = nil
		renderShow(groupName)
	end)
end

local function hide(groupName)
	if groupName == nil then
		cancelPendingShow()
		state.pendingGroupName = nil
		state.visibleGroupName = nil
		if state.canvas ~= nil then state.canvas:hide() end
		return
	end

	if state.pendingGroupName == groupName then
		cancelPendingShow()
		state.pendingGroupName = nil
	end

	if state.visibleGroupName == groupName then
		state.visibleGroupName = nil
		if state.canvas ~= nil then state.canvas:hide() end
	end
end

function M.setup(route)
	hs.urlevent.bind(route, function(_, params)
		local action = params["action"]

		if action == "show" then
			show(params["group"])
		elseif action == "hide" then
			hide(params["group"])
		end
	end)
end

return M
