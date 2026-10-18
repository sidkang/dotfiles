local toolbar = require("hs.webview.toolbar")
local console = require("hs.console")
local image = require("hs.image")

local M = {}

local state = {
	toolbar = nil,
}

local function buildToolbar()
	return toolbar
		.new("CustomToolbar", {
			{
				id = "prefs",
				label = "Preferences",
				image = image.imageFromName("NSPreferencesGeneral"),
				tooltip = "Open Preferences",
				fn = function()
					hs.openPreferences()
				end,
			},
			{
				id = "reload",
				label = "Reload config",
				image = image.imageFromName("NSSynchronize"),
				tooltip = "Reload configuration",
				fn = function()
					hs.reload()
				end,
			},
			{
				id = "clearLog",
				label = "Clear",
				image = image.imageFromName("NSTrashFull"),
				tooltip = "Clear Console",
				fn = function()
					console.clearConsole()
				end,
			},
			{
				id = "help",
				label = "Help",
				image = image.imageFromName("NSInfo"),
				tooltip = "Open API docs browser",
				fn = hs.doc.hsdocs.help,
			},
		})
		:canCustomize(true)
		:autosaves(true)
end

function M.setup()
	if state.toolbar == nil then
		state.toolbar = buildToolbar()
	end

	console.defaultToolbar = state.toolbar
	console.toolbar(state.toolbar)
end

return M
