-- Define the text you want to display
-- local M = {}
--
-- local text = [[
-- Line 1
-- Line 2
-- Line 3
-- Line 4
-- Line 5
-- Line 6
-- Line 7
-- Line 8
-- Line 9
-- Line 10
-- ]]
--
-- local key_bindings = {
-- 	["]"] = {
-- 		{ lhs = "w", desc = "window" },
-- 		{ lhs = "s", desc = "space" },
-- 	},
-- 	["["] = {
-- 		{ lhs = "w", desc = "window" },
-- 		{ lhs = "s", desc = "space" },
-- 	},
-- }
--
-- -- Split the text into lines
-- local lines = {}
-- for line in string.gmatch(text, "[^\r\n]+") do
-- 	table.insert(lines, line)
-- end
--
-- -- Create a new hs.canvas object
-- local screen = hs.screen.mainScreen()
-- local screenFrame = screen:frame()
-- local textFrame = {
-- 	x = screenFrame.w - 300, -- Adjust the width as needed
-- 	y = screenFrame.h - 220, -- Adjust the height as needed
-- 	w = 300,
-- 	h = 200,
-- }
--
-- local canvas = hs.canvas.new({
-- 	x = textFrame.x,
-- 	y = textFrame.y,
-- 	w = textFrame.w,
-- 	h = textFrame.h,
-- })
--
-- -- Set the background
-- canvas:appendElements({
-- 	action = "fill",
-- 	fillColor = { white = 1, alpha = 1 },
-- 	type = "rectangle",
-- 	roundedRectRadii = { xRadius = 10, yRadius = 10 },
-- })
--
-- -- Set the border
-- canvas:appendElements({
-- 	action = "stroke",
-- 	strokeColor = { black = 1, alpha = 1 },
-- 	strokeWidth = 2,
-- 	type = "rectangle",
-- 	roundedRectRadii = { xRadius = 10, yRadius = 10 },
-- })
--
-- -- Add text
-- for i, line in ipairs(lines) do
-- 	canvas:appendElements({
-- 		type = "text",
-- 		text = line,
-- 		textSize = 14,
-- 		textColor = { black = 1, alpha = 1 },
-- 		frame = { x = 10, y = 10 + (i - 1) * 18, w = textFrame.w - 20, h = 18 },
-- 	})
-- end
--
-- canvas:show()

-- Create a canvas at a specified position with defined width and height
local canvas = hs.canvas.new({ x = 100, y = 100, w = 300, h = 400 }):show()

-- Add elements to the canvas (title and a few shortcut descriptions)
canvas:appendElements({
	-- Background
	{
		type = "rectangle",
		action = "fill",
		fillColor = { hex = "#000000", alpha = 0.75 },
		frame = { x = "0%", y = "0%", w = "100%", h = "100%" },
	},
	-- Title
	{
		type = "text",
		text = "Shortcut Menu",
		textSize = 24,
		textColor = { hex = "#FFFFFF" },
		textAlignment = "center",
		frame = { x = "10%", y = "5%", w = "80%", h = "10%" },
	},
	-- Shortcut 1
	{
		type = "text",
		text = "Cmd + A: Action 1",
		textSize = 18,
		textColor = { hex = "#FFFFFF" },
		textAlignment = "left",
		frame = { x = "10%", y = "20%", w = "80%", h = "10%" },
	},
	-- Shortcut 2
	{
		type = "text",
		text = "Cmd + B: Action 2",
		textSize = 18,
		textColor = { hex = "#FFFFFF" },
		textAlignment = "left",
		frame = { x = "10%", y = "35%", w = "80%", h = "10%" },
	},
	-- Shortcut 3
	{
		type = "text",
		text = "Cmd + C: Action 3",
		textSize = 18,
		textColor = { hex = "#FFFFFF" },
		textAlignment = "left",
		frame = { x = "10%", y = "50%", w = "80%", h = "10%" },
	},
})

-- Initially hide the canvas
canvas:show()
