-- Run URL routes over Hammerspoon IPC: `hs -c 'hsurl("route?a=b")'` takes the same
-- strings as hammerspoon://route?a=b, without the ~60 ms `open` round trip.
local M = {}

local routes = {}
local installed = false

local function decode(text)
	return (text:gsub("%%(%x%x)", function(hex) return string.char(tonumber(hex, 16)) end))
end

local function parse(url)
	local route, query = url:match("^([^?]*)%??(.*)$")
	local params = {}
	for pair in query:gmatch("[^&]+") do
		local key, value = pair:match("^([^=]*)=?(.*)$")
		params[decode(key)] = decode(value)
	end
	return route:lower(), params
end

--- Must run before the modules that call hs.urlevent.bind.
function M.setup()
	if installed then return end
	installed = true

	local bind = hs.urlevent.bind
	hs.urlevent.bind = function(name, callback)
		routes[name:lower()] = callback
		return bind(name, callback)
	end

	function _G.hsurl(url)
		local route, params = parse(url)
		local callback = routes[route]
		if callback == nil then error("unknown route: " .. route, 0) end
		callback(route, params)
	end
end

return M
