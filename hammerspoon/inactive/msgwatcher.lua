local M = {}

local applescript = [[
on run {targetBuddy}
    tell application "Messages"
        set targetService to 1st service whose service type = iMessage
        set targetBuddy to buddy targetBuddy of targetService
        set lastMessage to last text message of targetBuddy
    end tell
    return lastMessage
end run
]]

local function runAppleScript(targetBuddy)
	local ok, result, err = hs.osascript.applescript(applescript, { targetBuddy })
	if not ok then return nil, err or "failed to read message" end

	return result, nil
end

function M.getLastMessage(targetBuddy)
	if targetBuddy == nil or targetBuddy == "" then
		return nil, "missing target buddy"
	end

	return runAppleScript(targetBuddy)
end

function M.setup(route)
	hs.urlevent.bind(route, function(_, params)
		local message, err = M.getLastMessage(params["buddy"])
		if message ~= nil then
			hs.alert.show(message)
		else
			hs.alert.show(err or "failed to read message")
		end
	end)
end

return M
