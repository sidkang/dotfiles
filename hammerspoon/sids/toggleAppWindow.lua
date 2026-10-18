local M = {}

local function notify(message)
	hs.alert.show(message)
end

local function findMatchingWindow(windows, window_title)
	if windows == nil then return nil end

	return hs.fnutils.find(windows, function(window)
		local title = window:title()
		return title ~= nil and title:find(window_title) ~= nil
	end)
end

-- M.findAppOrWindow = function(app_id, win_title)
-- 	local app = hs.application.get(app_id)
-- 	if not app then
-- 		hs.alert.show("Application with app_id " .. app_id .. " not found")
-- 		return nil
-- 	end
--
-- 	-- Get all windows of the application
-- 	local windows = app:allWindows()
--
-- 	-- Loop through all windows to find the one containing the specified string in the title
-- 	for _, window in ipairs(windows) do
-- 		local windowTitle = window:title()
-- 		if windowTitle:find(title_string) then
-- 			hs.alert.show("Window found: " .. windowTitle)
-- 			return window
-- 		end
-- 	end
--
-- 	hs.alert.show("No window containing '" .. title_string .. "' found in application with app_id " .. app_id)
-- 	return nil
-- end

M.toggleWindow = function(app_id, window_title)
	local app = hs.application.find(app_id)
	local space = hs.spaces.focusedSpace()

	if app then
		local windows = app:allWindows()
		if window_title ~= nil then
			local win = findMatchingWindow(windows, window_title)
			if win == nil then
				notify("Window not found")
				return
			end

			if win:isVisible() then
				win:minimize()
			else
				win:focus()
			end
			return
		else
			if app:isFrontmost() then
				app:hide()
			else
				local mainWindow = app:mainWindow()
				if mainWindow == nil then
					notify("App window not found")
					return
				end

				hs.spaces.moveWindowToSpace(mainWindow, space)
				app:activate()
			end
		end
	else
		notify("Open App")
		hs.application.launchOrFocusByBundleID(app_id)
	end
end

M.setup = function(route)
	hs.urlevent.bind(route, function(_, params)
		M.toggleWindow(params["appid"], params["win_title"])
	end)
end

return M
