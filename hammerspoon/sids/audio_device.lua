local M = {}

local config = {
	quietOnWifi = {
		hostname = "glacier",
		ssid = "CCX-Guest",
		outputDeviceUID = "BuiltInSpeakerDevice",
		outputDeviceName = "MacBook Air Speakers",
		volume = 0,
	},

	preferredInput = {
		djiMicMini = "Wireless Mic Rx",
	},
}

local state = {
	wifiWatcher = nil,
	audioWatcherStarted = false,
}

local function notify(title, message)
	hs.notify.new({ title = title, informativeText = message }):send()
end

local function currentHostname()
	local hostname = hs.host.localizedName()
	if hostname == nil then return nil end

	return string.lower(hostname)
end

local function isQuietHost()
	return currentHostname() == string.lower(config.quietOnWifi.hostname)
end

local function currentSSID()
	local ssid = hs.wifi.currentNetwork()
	if ssid ~= nil then return ssid end

	for _, interface in ipairs(hs.wifi.interfaces()) do
		local details = hs.wifi.interfaceDetails(interface)
		if details ~= nil and details.ssid ~= nil then return details.ssid end
	end

	return nil
end

local function isQuietOutputDevice(device)
	if device == nil then return false end

	return device:uid() == config.quietOnWifi.outputDeviceUID or device:name() == config.quietOnWifi.outputDeviceName
end

local function quietOutputOnWifi()
	if not isQuietHost() then return end
	if currentSSID() ~= config.quietOnWifi.ssid then return end

	local outputDevice = hs.audiodevice.defaultOutputDevice()
	if not isQuietOutputDevice(outputDevice) then return end
	if outputDevice:volume() == config.quietOnWifi.volume then return end

	outputDevice:setVolume(config.quietOnWifi.volume)
	notify("Audio Device", "Quieted MacBook Air speakers on " .. config.quietOnWifi.ssid)
end

local function preferredInputDevice()
	return hs.audiodevice.findInputByName(config.preferredInput.djiMicMini)
end

local function selectPreferredInput()
	local inputDevice = preferredInputDevice()
	if inputDevice == nil then return end

	local currentInput = hs.audiodevice.defaultInputDevice()
	if currentInput ~= nil and currentInput:name() == inputDevice:name() then return end

	inputDevice:setDefaultInputDevice()
	notify("Audio Device", "Selected input: " .. inputDevice:name())
end

local function handleWifiChange()
	quietOutputOnWifi()
end

local function handleAudioDeviceChange()
	quietOutputOnWifi()
	selectPreferredInput()
end

function M.setup()
	if state.wifiWatcher == nil then
		state.wifiWatcher = hs.wifi.watcher.new(handleWifiChange)
		state.wifiWatcher:start()
	end

	if not state.audioWatcherStarted then
		hs.audiodevice.watcher.setCallback(handleAudioDeviceChange)
		hs.audiodevice.watcher.start()
		state.audioWatcherStarted = true
	end

	quietOutputOnWifi()
	selectPreferredInput()
end

return M
