local M = {}

-- local methods = {
-- 	cn = function() hs.keycodes.setMethod("Shuangpin – Simplified") end,
-- 	ja = function() hs.keycodes.setMethod("Hiragana") end,
-- 	en = function() hs.keycodes.setLayout("ABC") end,
-- }

local methods = {
	cn = function() hs.keycodes.currentSourceID("com.apple.inputmethod.SCIM.Shuangpin") end,
	ja = function() hs.keycodes.currentSourceID("com.apple.inputmethod.Japanese.Hiragana") end,
	en = function() hs.keycodes.currentSourceID("com.apple.keylayout.ABC") end,
}

local function notify(message) hs.alert.show(message) end

local function switchIME(to)
	local action = methods[to]
	if action == nil then
		notify("Invalid method for switchIME")
		return
	end
	if to ~= "en" then
		methods["en"]()
		hs.timer.doAfter(0.02, action)
	else
		action()
	end
end

function M.setup(route)
	hs.urlevent.bind(route, function(_, params)
		local target = params["to"]
		if target == nil then
			notify("Missing target IME")
			return
		end

		switchIME(target)
	end)
end

return M
