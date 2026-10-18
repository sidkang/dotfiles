local utils = require("hs.fnutils")

local M = {}

local action_list = { "selectionTranslate", "snipTranslate", "pasteboardTranslate" }

local bob_applescript = [[
use scripting additions
use framework "Foundation"
on callBob(recordValue)
	set theParameter to (((current application's NSString)'s alloc)'s initWithData:((current application's NSJSONSerialization)'s dataWithJSONObject:recordValue options:1 |error|:(missing value)) encoding:4) as string
	tell application id "com.hezongyidev.Bob" to request theParameter
end callBob
]]

local function notify(message)
	hs.alert.show(message)
end

local function isValidAction(action)
	return action ~= nil and utils.contains(action_list, action)
end

local function callBob(action)
	if not isValidAction(action) then
		notify("BOB: invalid action")
		return
	end

	local ok, _, err = hs.osascript.applescript(
		bob_applescript .. 'callBob({|path|:"translate", body:{action:"' .. action .. '"}})'
	)

	if not ok then notify(err or "BOB: request failed") end
end

function M.setup(route)
	hs.urlevent.bind(route, function(_, params)
		local action = params["action"]
		if action == nil then
			notify("BOB: missing action")
			return
		end

		callBob(action)
	end)
end

return M
