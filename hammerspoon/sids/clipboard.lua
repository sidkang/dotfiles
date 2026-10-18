local M = {}

local state = {
	watcher = nil,
	lastMagnetLink = nil,
}

local envKeys = {
	host = "HAMMERSPOON_TRANSMISSION_HOST",
	port = "HAMMERSPOON_TRANSMISSION_PORT",
	user = "HAMMERSPOON_TRANSMISSION_USER",
	password = "HAMMERSPOON_TRANSMISSION_PASSWORD",
}

local function notify(title, message)
	hs.notify.new({ title = title, informativeText = message }):send()
end

local function readConfig()
	local host = os.getenv(envKeys.host)
	local port = os.getenv(envKeys.port) or "443"
	local user = os.getenv(envKeys.user)
	local password = os.getenv(envKeys.password)

	if host == nil or user == nil or password == nil then
		return nil, string.format(
			"missing env: %s, %s, %s",
			envKeys.host,
			envKeys.user,
			envKeys.password
		)
	end

	return {
		host = host,
		port = tonumber(port) or 443,
		user = user,
		password = password,
	}
	end

local function transmissionURL(config)
	return string.format("https://%s:%d/transmission/rpc", config.host, config.port)
end

local function authHeaders(config)
	return {
		Authorization = "Basic " .. hs.base64.encode(config.user .. ":" .. config.password),
	}
end

local function extractSessionId(headers)
	if headers == nil then return nil end

	return headers["X-Transmission-Session-Id"] or headers["x-transmission-session-id"]
end

local function addMagnetLinkToTransmission(magnetLink)
	local config, err = readConfig()
	if config == nil then
		notify("Transmission Tool", err)
		return
	end

	local url = transmissionURL(config)
	hs.http.asyncGet(url, authHeaders(config), function(status, _, headers)
		if status ~= 409 then
			notify("Transmission Tool", "failed to retrieve session ID")
			return
		end

		local sessionId = extractSessionId(headers)
		if sessionId == nil then
			notify("Transmission Tool", "missing Transmission session ID")
			return
		end

		local payload = hs.json.encode({
			method = "torrent-add",
			arguments = {
				filename = magnetLink,
			},
		})

		local headersWithSession = authHeaders(config)
		headersWithSession["X-Transmission-Session-Id"] = sessionId
		headersWithSession["Content-Type"] = "application/json"

		hs.http.asyncPost(url, payload, headersWithSession, function(postStatus, body, _)
			if postStatus ~= 200 then
				notify("Transmission Tool", "failed to add magnet link")
				return
			end

			local response = hs.json.decode(body or "") or {}
			if response.result == "success" then
				notify("Transmission Tool", "magnet link added successfully")
			else
				notify("Transmission Tool", response.result or "failed to add magnet link")
			end
		end)
	end)
end

local function handlePasteboardChange()
	local currentClipboardContents = hs.pasteboard.getContents()
	if currentClipboardContents == nil then return end
	if not string.match(currentClipboardContents, "^magnet:") then return end
	if currentClipboardContents == state.lastMagnetLink then return end

	state.lastMagnetLink = currentClipboardContents
	addMagnetLinkToTransmission(currentClipboardContents)
end

function M.setup()
	if state.watcher ~= nil then return end

	state.watcher = hs.pasteboard.watcher.new(handlePasteboardChange)
	state.watcher:start()
end

return M
