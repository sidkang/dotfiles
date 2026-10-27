local M = {}

local config = {
	intervalSeconds = 60 * 60,
	query = "Mac Wallpaper",
	wallpaperDir = "~/Pictures/wallpapers/unsplash",
	processedDirName = "processed",
	notchMinPt = 30, -- ponytail: Hammerspoon has no notch API; auto-hidden menu bar reports 0, so notch masking is skipped then.
	notchScreenNameMarkers = { "Built-in", "内建", "內建", "内置" },
	minDownloadWidth = 3840,
}

local state = {
	busy = false,
	timer = nil,
	screenWatcher = nil,
	tasks = {},
	sourcePath = nil,
	sourceID = nil,
}

local function notify(message)
	hs.notify.new({ title = "Unsplash Wallpaper", informativeText = message }):send()
end

local function round(value)
	return math.floor(value + 0.5)
end

local function expandPath(path)
	return (path:gsub("^~", os.getenv("HOME") or ""))
end

local function shquote(value)
	return "'" .. tostring(value):gsub("'", "'\\''") .. "'"
end

local function ensureDir(path)
	hs.execute("/bin/mkdir -p " .. shquote(path))
end

local function urlEncode(value)
	return tostring(value):gsub("([^%w%-%._~])", function(char)
		return string.format("%%%02X", string.byte(char))
	end)
end

local function fileURL(path)
	return "file://" .. path:gsub("([^%w%-%._~/%:])", function(char)
		return string.format("%%%02X", string.byte(char))
	end)
end

local function sanitize(value)
	return tostring(value):gsub("[^%w%-%._]", "_")
end

local function apiKey()
	local key = os.getenv("UNSPLASH_API_KEY")
	if key ~= nil and key ~= "" then return key end
	return hs.settings.get("UNSPLASH_API_KEY")
end

local function decodedJSON(body)
	local ok, decoded = pcall(hs.json.decode, body)
	if not ok then return nil end
	return decoded
end

local function isOK(code)
	return type(code) == "number" and code >= 200 and code < 300
end

local function magickPath()
	for _, path in ipairs({ "/opt/homebrew/bin/magick", "/usr/local/bin/magick", "/opt/homebrew/bin/convert", "/usr/local/bin/convert" }) do
		if hs.fs.attributes(path) ~= nil then return path end
	end

	local output, ok = hs.execute("PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin command -v magick")
	if ok and output ~= nil and output ~= "" then return output:gsub("%s+$", "") end

	return nil
end

local function isNotchCandidate(screen)
	local name = screen:name() or ""
	for _, marker in ipairs(config.notchScreenNameMarkers) do
		if name:find(marker, 1, true) ~= nil then return true end
	end
	return false
end

local function screenGeometry(screen)
	local full = screen:fullFrame()
	local usable = screen:frame()
	local mode = screen:currentMode() or {}
	local scale = mode.scale or 1
	local topPt = math.max(0, usable.y - full.y)
	local barPt = isNotchCandidate(screen) and topPt >= config.notchMinPt and topPt or 0
	local width = round(full.w * scale)
	local height = round(full.h * scale)
	local bar = math.min(round(barPt * scale), height - 1)

	return {
		width = width,
		height = height,
		bar = bar,
		contentHeight = height - bar,
	}
end

local function maxScreenDimension()
	local size = config.minDownloadWidth
	for _, screen in ipairs(hs.screen.allScreens()) do
		local geometry = screenGeometry(screen)
		size = math.max(size, geometry.width, geometry.height)
	end
	return size
end

local function imageURL(photo)
	local urls = photo.urls or {}
	local raw = urls.raw or urls.full or urls.regular
	if raw == nil then return nil end

	local separator = raw:find("?", 1, true) and "&" or "?"
	return raw .. separator .. "w=" .. maxScreenDimension() .. "&fm=jpg&q=90"
end

local function processedPath(sourceID, screen)
	local dir = expandPath(config.wallpaperDir) .. "/" .. config.processedDirName
	ensureDir(dir)

	local screenID = screen.getUUID and screen:getUUID() or screen:id() or screen:name() or "screen"
	return string.format("%s/%s-%s.jpg", dir, sanitize(sourceID), sanitize(screenID))
end

local function applyToScreen(sourcePath, sourceID, screen)
	local magick = magickPath()
	if magick == nil then
		notify("Install ImageMagick: brew install imagemagick")
		return
	end

	local geometry = screenGeometry(screen)
	local outputPath = processedPath(sourceID, screen)
	local size = geometry.width .. "x" .. geometry.contentHeight
	local finalSize = geometry.width .. "x" .. geometry.height
	local targetScreen = screen

	local args = {
		sourcePath,
		"-auto-orient",
		"-resize",
		size .. "^",
		"-gravity",
		"center",
		"-extent",
		size,
		"-background",
		"black",
		"-gravity",
		"south",
		"-extent",
		finalSize,
		outputPath,
	}

	local task = hs.task.new(magick, function(exitCode, _, stderr)
		state.tasks[outputPath] = nil
		if sourceID ~= state.sourceID then return end
		if exitCode ~= 0 then
			notify("ImageMagick failed: " .. tostring(stderr or exitCode))
			return
		end
		targetScreen:desktopImageURL(fileURL(outputPath))
	end, args)

	if task == nil then
		notify("Failed to create ImageMagick task")
		return
	end

	state.tasks[outputPath] = task
	if not task:start() then
		state.tasks[outputPath] = nil
		notify("Failed to start ImageMagick")
	end
end

local function applyToScreens(sourcePath, sourceID)
	for _, screen in ipairs(hs.screen.allScreens()) do
		applyToScreen(sourcePath, sourceID, screen)
	end
end

local function trackDownload(photo, key)
	local location = photo.links and photo.links.download_location
	if location == nil then return end

	hs.http.asyncGet(location, { Authorization = "Client-ID " .. key }, function() end)
end

local function savePhoto(photo, body)
	local dir = expandPath(config.wallpaperDir)
	ensureDir(dir)

	local sourceID = photo.id or tostring(os.time())
	local path = string.format("%s/%s.jpg", dir, sanitize(sourceID))
	local file = io.open(path, "wb")
	if file == nil then
		notify("Cannot write " .. path)
		return nil
	end

	file:write(body)
	file:close()
	return path, sourceID
end

local function downloadPhoto(photo, key)
	local url = imageURL(photo)
	if url == nil then
		notify("Unsplash photo has no image URL")
		state.busy = false
		return
	end

	hs.http.asyncGet(url, { Accept = "image/jpeg" }, function(code, body)
		state.busy = false
		if not isOK(code) then
			notify("Image download failed: HTTP " .. tostring(code))
			return
		end
		if body == nil or body == "" then
			notify("Image download was empty")
			return
		end

		local sourcePath, sourceID = savePhoto(photo, body)
		if sourcePath == nil then return end

		state.sourcePath = sourcePath
		state.sourceID = sourceID
		trackDownload(photo, key)
		applyToScreens(sourcePath, sourceID)
	end)
end

function M.refresh()
	if state.busy then return end

	local key = apiKey()
	if key == nil or key == "" then
		notify("Missing UNSPLASH_API_KEY")
		return
	end

	state.busy = true
	local url = "https://api.unsplash.com/photos/random?orientation=landscape&content_filter=high&query=" .. urlEncode(config.query)
	hs.http.asyncGet(url, { Authorization = "Client-ID " .. key, Accept = "application/json" }, function(code, body)
		if not isOK(code) then
			state.busy = false
			notify("Unsplash API failed: HTTP " .. tostring(code))
			return
		end

		local photo = decodedJSON(body)
		if type(photo) ~= "table" then
			state.busy = false
			notify("Unsplash API returned invalid JSON")
			return
		end

		downloadPhoto(photo, key)
	end)
end

function M.setup()
	ensureDir(expandPath(config.wallpaperDir))
	if apiKey() == nil or apiKey() == "" then
		notify("Missing UNSPLASH_API_KEY")
		return
	end

	if state.timer == nil then
		state.timer = hs.timer.doEvery(config.intervalSeconds, M.refresh)
	end

	if state.screenWatcher == nil then
		state.screenWatcher = hs.screen.watcher.new(function()
			hs.timer.doAfter(1, function()
				if state.sourcePath ~= nil then applyToScreens(state.sourcePath, state.sourceID) end
			end)
		end)
		state.screenWatcher:start()
	end

	M.refresh()
end

return M
