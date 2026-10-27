-- Layout and drawing for the key guide card. Pure: group + screen frame in, canvas elements out.
local M = {}

local palettes = {
	light = { -- catppuccin latte
		red = "#d20f39", peach = "#fe640b", yellow = "#df8e1d", green = "#40a02b", teal = "#179299", sky = "#04a5e5",
		sapphire = "#209fb5", blue = "#1e66f5", lavender = "#7287fd", mauve = "#8839ef", pink = "#ea76cb",
		text = "#4c4f69", subtext = "#6c6f85", muted = "#8c8fa1",
		card = "#eff1f5", border = "#bcc0cc", divider = "#ccd0da", keycap = "#e6e9ef", keycapBorder = "#bcc0cc",
		shadow = "#4c4f69",
	},
	dark = { -- catppuccin mocha
		red = "#f38ba8", peach = "#fab387", yellow = "#f9e2af", green = "#a6e3a1", teal = "#94e2d5", sky = "#89dceb",
		sapphire = "#74c7ec", blue = "#89b4fa", lavender = "#b4befe", mauve = "#cba6f7", pink = "#f5c2e7",
		text = "#cdd6f4", subtext = "#a6adc8", muted = "#7f849c",
		card = "#1e1e2e", border = "#45475a", divider = "#313244", keycap = "#313244", keycapBorder = "#45475a",
		shadow = "#000000",
	},
}

local layout = {
	margin = 28, -- transparent space around the card for the shadow
	screenGap = 24, -- card distance from the screen edge
	padding = 18,
	radius = 16,
	titleSize = 16,
	titleHeight = 22,
	headerGap = 12,
	rowHeight = 30,
	keycapHeight = 22,
	keycapRadius = 6,
	keycapPadding = 9,
	keycapMinWidth = 26,
	keyGap = 12,
	columnGap = 30,
	maxRowsPerColumn = 8,
	footerGap = 10,
	footerHeight = 16,
}

local fonts = { text = ".AppleSystemUIFont", title = ".AppleSystemUIFontEmphasized", key = "Menlo-Bold" }
local sizes = { text = 14, key = 12, footer = 12 }

local measureCanvas

local function palette()
	return hs.host.interfaceStyle() == "Dark" and palettes.dark or palettes.light
end

local function rgb(hex, alpha) return { hex = hex, alpha = alpha or 1 } end

local function styled(text, font, size, color, alignment)
	return hs.styledtext.new(text, {
		font = { name = font, size = size },
		color = color,
		paragraphStyle = alignment and { alignment = alignment } or nil,
	})
end

local function measure(styledText)
	if measureCanvas == nil then
		measureCanvas = hs.canvas.new({ x = 0, y = 0, w = 10, h = 10 })
		measureCanvas:appendElements({ type = "text", text = "", frame = { x = 0, y = 0, w = 10, h = 10 } })
	end
	return math.ceil(measureCanvas:minimumTextSize(1, styledText).w)
end

--- "{accent|color} plain" -> styled text with accent runs coloured from the palette.
local function descText(desc, colors)
	local result = styled("", fonts.text, sizes.text, rgb(colors.subtext))
	local cursor = 1
	while cursor <= #desc do
		local first, last, token = desc:find("{(.-)}", cursor)
		if first == nil then
			result = result .. styled(desc:sub(cursor), fonts.text, sizes.text, rgb(colors.subtext))
			break
		end
		if first > cursor then result = result .. styled(desc:sub(cursor, first - 1), fonts.text, sizes.text, rgb(colors.subtext)) end
		local text, name = token:match("^(.-)|([%a_]+)$")
		result = result .. styled(text or token, fonts.text, sizes.text, rgb(colors[name or "peach"] or colors.peach))
		cursor = last + 1
	end
	return result
end

local function splitColumns(items)
	local columns = #items > layout.maxRowsPerColumn and 2 or 1
	local rows = math.ceil(#items / columns)
	local result = {}
	for column = 1, columns do
		result[column] = table.move(items, (column - 1) * rows + 1, math.min(column * rows, #items), 1, {})
	end
	return result, rows
end

---@param group { title: string, exit: boolean?, footer: string?, items: { key: string, desc: string }[] }
---@param screenFrame table
---@return table frame, table[] elements
function M.build(group, screenFrame)
	local colors = palette()
	local columns, rows = splitColumns(group.items)

	local measured = {}
	local contentWidth = 0
	for columnIndex, items in ipairs(columns) do
		local keyWidth, textWidth = layout.keycapMinWidth, 0
		measured[columnIndex] = {}
		for rowIndex, item in ipairs(items) do
			local key = styled(item.key, fonts.key, sizes.key, rgb(colors.text), "center")
			local desc = descText(item.desc, colors)
			measured[columnIndex][rowIndex] = { key = key, desc = desc }
			keyWidth = math.max(keyWidth, measure(key) + layout.keycapPadding * 2)
			textWidth = math.max(textWidth, measure(desc))
		end
		measured[columnIndex].keyWidth = keyWidth
		measured[columnIndex].width = keyWidth + layout.keyGap + textWidth
		contentWidth = contentWidth + measured[columnIndex].width + (columnIndex > 1 and layout.columnGap or 0)
	end

	local title = styled(group.title, fonts.title, layout.titleSize, rgb(colors.text))
	local footerText = group.footer or (group.exit and "Caps 退出") or nil
	local footer = footerText and styled(footerText, fonts.text, sizes.footer, rgb(colors.muted))
	contentWidth = math.max(contentWidth, measure(title), footer and measure(footer) or 0)

	local cardWidth = contentWidth + layout.padding * 2
	local bodyTop = layout.padding + layout.titleHeight + layout.headerGap
	local bodyHeight = rows * layout.rowHeight
	local cardHeight = bodyTop + bodyHeight + layout.padding
	if footer then cardHeight = cardHeight + layout.footerGap + layout.footerHeight end

	local margin = layout.margin
	local frame = {
		x = screenFrame.x + screenFrame.w - cardWidth - margin * 2 - layout.screenGap + margin,
		y = screenFrame.y + screenFrame.h - cardHeight - margin * 2 - layout.screenGap + margin,
		w = cardWidth + margin * 2,
		h = cardHeight + margin * 2,
	}

	local elements = {
		{
			type = "rectangle",
			action = "fill",
			roundedRectRadii = { xRadius = layout.radius, yRadius = layout.radius },
			fillColor = rgb(colors.card, 0.97),
			withShadow = true,
			shadow = { blurRadius = 26, color = rgb(colors.shadow, 0.28), offset = { h = -8, w = 0 } },
			frame = { x = margin, y = margin, w = cardWidth, h = cardHeight },
		},
		{
			type = "rectangle",
			action = "stroke",
			strokeWidth = 1,
			roundedRectRadii = { xRadius = layout.radius, yRadius = layout.radius },
			strokeColor = rgb(colors.border, 0.9),
			frame = { x = margin + 0.5, y = margin + 0.5, w = cardWidth - 1, h = cardHeight - 1 },
		},
		{
			type = "text",
			text = title,
			frame = { x = margin + layout.padding, y = margin + layout.padding, w = contentWidth, h = layout.titleHeight },
		},
		{
			type = "segments",
			action = "stroke",
			strokeWidth = 1,
			strokeColor = rgb(colors.divider),
			coordinates = {
				{ x = margin + layout.padding, y = margin + layout.padding + layout.titleHeight + layout.headerGap / 2 },
				{ x = margin + cardWidth - layout.padding, y = margin + layout.padding + layout.titleHeight + layout.headerGap / 2 },
			},
		},
	}

	local columnX = margin + layout.padding
	for columnIndex, items in ipairs(columns) do
		local info = measured[columnIndex]
		for rowIndex = 1, #items do
			local rowTop = margin + bodyTop + (rowIndex - 1) * layout.rowHeight
			local keycapTop = rowTop + (layout.rowHeight - layout.keycapHeight) / 2
			local cell = info[rowIndex]
			local radii = { xRadius = layout.keycapRadius, yRadius = layout.keycapRadius }
			elements[#elements + 1] = {
				type = "rectangle",
				action = "fill",
				roundedRectRadii = radii,
				fillColor = rgb(colors.keycap),
				frame = { x = columnX, y = keycapTop, w = info.keyWidth, h = layout.keycapHeight },
			}
			elements[#elements + 1] = {
				type = "rectangle",
				action = "stroke",
				strokeWidth = 1,
				roundedRectRadii = radii,
				strokeColor = rgb(colors.keycapBorder),
				frame = { x = columnX + 0.5, y = keycapTop + 0.5, w = info.keyWidth - 1, h = layout.keycapHeight - 1 },
			}
			elements[#elements + 1] = {
				type = "text",
				text = cell.key,
				frame = { x = columnX, y = keycapTop + 3, w = info.keyWidth, h = layout.keycapHeight },
			}
			elements[#elements + 1] = {
				type = "text",
				text = cell.desc,
				frame = { x = columnX + info.keyWidth + layout.keyGap, y = rowTop + 5, w = info.width - info.keyWidth - layout.keyGap + 4, h = layout.rowHeight },
			}
		end
		columnX = columnX + info.width + layout.columnGap
	end

	if footer then
		elements[#elements + 1] = {
			type = "text",
			text = footer,
			frame = { x = margin + layout.padding, y = margin + cardHeight - layout.padding - layout.footerHeight + 1, w = contentWidth, h = layout.footerHeight },
		}
	end

	return frame, elements
end

return M
