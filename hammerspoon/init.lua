local function bootstrap()
	hs.loadSpoon("SpoonInstall")
	spoon.SpoonInstall.use_syncinstall = true

	local install = spoon.SpoonInstall
	if false then install:andUse("EmmyLua") end

	-- require("hs.ipc").cliInstall("/opt/homebrew")
	hs.ipc.cliInstall(os.getenv("HOME") .. "/.local", true)
	hs.window.animationDuration = 0
end

local alertColors = {
	debug = hs.drawing.color.x11.gray,
	info = hs.drawing.color.x11.seagreen,
	warning = hs.drawing.color.x11.slateblue,
	error = hs.drawing.color.x11.crimson,
	critical = hs.drawing.color.x11.indianred,
}

local function configureAlerts()
	hs.alert.defaultStyle = {
		strokeWidth = 0,
		textColor = { white = 1, alpha = 1 },
		textFont = "LXGW WenKai GB",
		textSize = 28,
		radius = 8,
		atScreenEdge = 0,
		fadeInDuration = 0.20,
		fadeOutDuration = 0.50,
		padding = nil,
	}
end

local function focusedAlertScreen()
	local window = hs.window.focusedWindow()
	if window ~= nil then return window:screen() end

	return hs.mouse.getCurrentScreen() or hs.screen.mainScreen()
end

local function showAlert(message, level)
	local color = alertColors[level or "info"] or alertColors.info
	hs.alert.show(message, {
		strokeColor = color,
		fillColor = color,
	}, focusedAlertScreen())
end

local function bindDevRoutes()
	hs.urlevent.bind("clearconsole", hs.console.clearConsole)
	hs.urlevent.bind("reloadconfig", hs.reload)
	hs.urlevent.bind("openconsole", hs.openConsole)
	hs.urlevent.bind("notify", function(_, params) showAlert(params["msg"] or "Ok", params["level"]) end)
	hs.urlevent.bind("appInfo", function()
		local window = hs.window.focusedWindow()
		local app = window and window:application() or nil
		if app == nil then
			showAlert("No focused window", "warning")
			return
		end

		showAlert("App path:      " .. app:path() .. "\n" .. "App name:      " .. app:name() .. "\n" .. "IM source ID:  " .. hs.keycodes.currentSourceID())
	end)
end

local function setupModules()
	require("sids.applescript").setup("scpt")
	require("sids.ime").setup("switchime")
	require("sids.bob").setup("callbob")
	require("sids.whichkey").setup("whichkey")
	require("sids.console-toolbar").setup()
	require("sids.daily_tasks").setup()
	require("sids.clipboard").setup()
	require("sids.color_meter").setup()
	require("sids.float_window").setup("floatwindow")
	require("sids.aerospace_window_hints").setup("aswindowhints")
	require("sids.audio_device").setup()
end

bootstrap()
configureAlerts()
bindDevRoutes()
setupModules()
showAlert("Load Complete", "error")
