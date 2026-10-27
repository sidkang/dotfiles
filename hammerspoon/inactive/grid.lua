local window = require("hs.window")
local spaces = require("hs.spaces")
local grid = require("hs.grid")

grid.resizePushLeft = function(win)
	win = win or hs.window.focusedWindow()
	local g = grid.getGrid(win:screen())
	grid.adjustWindow(function(f)
		f.x = 0
		f.y = 0
		f.w = 0.5 * g.w
		f.h = 1 * g.h
	end, win)
end

grid.resizePushRight = function(win)
	win = win or hs.window.focusedWindow()
	local g = grid.getGrid(win:screen())
	grid.adjustWindow(function(f)
		f.x = 0.5 * g.w
		f.y = 0
		f.w = 0.5 * g.w
		f.h = 1 * g.h
	end, win)
end

grid.resizePushUp = function(win)
	win = win or hs.window.focusedWindow()
	local g = grid.getGrid(win:screen())
	grid.adjustWindow(function(f)
		f.x = 0
		f.y = 0
		f.w = 1 * g.w
		f.h = 0.5 * g.h
	end, win)
end

grid.resizePushDown = function(win)
	win = win or hs.window.focusedWindow()
	local g = grid.getGrid(win:screen())
	grid.adjustWindow(function(f)
		f.x = 0
		f.y = 0.5 * g.h
		f.w = 1 * g.w
		f.h = 0.5 * g.h
	end, win)
end

-- function grid.shoveWindowLeft(win)
-- 	if win == nil then
-- 		win = hs.window.focusedWindow()
-- 	end
-- 	local sg = grid.getGrid(window:screen())
-- 	local sw, sh = sg.w, sg.h
-- 	local function shoveLeft(wg)
-- 		wg.x = 0
-- 	end
--
-- 	grid.adjustWindow(shoveLeft, win)
-- end

function spaces.MoveWindowToSideSpace(direction, win)
	win = win or hs.window.focusedWindow()

	local screen = win:screen()
	local uuid = screen:getUUID()
	local userSpaces = nil

	for k, v in pairs(spaces.allSpaces()) do
		userSpaces = v
		if k == uuid then
			break
		end
	end
	if not userSpaces then
		return
	end
	local winSpace = spaces.windowSpaces(win)
	if not winSpace then
		return
	else
		winSpace = winSpace[1]
	end

	local first = nil
	local last = nil
	local skipSpaces = 0

	for _, spc in ipairs(userSpaces) do
		if spaces.spaceType(spc) ~= "user" then
			skipSpaces = skipSpaces + 1
		else
			if last and ((direction == "left" and spc == winSpace) or (direction == "right" and last == winSpace)) then
				local newSpace = (direction == "left" and last or spc)
				-- if switch then
				-- spaces.gotoSpace(newSpace) -- also possible, invokes MC
				-- end
				spaces.moveWindowToSpace(win, newSpace)

				-- Swich Space
				-- switchSpace(skipSpaces + 1, direction)
				-- hs.eventtap.keyStroke({ "ctrl", "alt" }, direction, 0)  -- "fn" is a bugfix for this combination, werid~
				if direction == "left" then
					hs.eventtap.keyStroke({ "ctrl", "alt" }, ",", 0) -- "fn" is a bugfix!
				else
					hs.eventtap.keyStroke({ "ctrl", "alt" }, ".", 0) -- "fn" is a bugfix!
				end
				return
			end
			last = spc
			skipSpaces = 0
		end
	end
end

function grid.pushWindowOtherScreen(win)
	win = win or hs.window.focusedWindow()
	local winscreen = win:screen()
	win:moveToScreen(winscreen:next())
	return grid.snap(win)
end
