local M = {}

local config = {
	quietOnWifi = {
		hostname = "glacier",
		ssid = "CCX-Guest",
		outputDeviceUID = "BuiltInSpeakerDevice",
		outputDeviceName = "MacBook Air Speakers",
		volume = 0,
		graceSeconds = 15,
		snoozeSetting = "audioDevice.quietUntil",
	},

	preferredInput = {
		djiMicMini = "Wireless Mic Rx",
	},
}

local state = {
	wifiWatcher = nil,
	audioWatcherStarted = false,
	wakeWatcher = nil,
	pendingQuiet = nil,
	snoozeTimer = nil,
	initialized = false,
	lastSSID = nil,
	lastOutputUID = nil,
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

local function quietOutputDevice()
	if not isQuietHost() then return nil end
	if currentSSID() ~= config.quietOnWifi.ssid then return nil end

	local device = hs.audiodevice.defaultOutputDevice()
	if not isQuietOutputDevice(device) then return nil end
	if device:volume() == config.quietOnWifi.volume then return nil end

	return device
end

local function cancelPendingQuiet()
	local pending = state.pendingQuiet
	if pending == nil then return end

	state.pendingQuiet = nil
	if pending.timer ~= nil then pending.timer:stop() end
	if pending.notification ~= nil then pending.notification:withdraw() end
end

local quietOutputOnWifi

local function scheduleSnoozeCheck()
	if state.snoozeTimer ~= nil then
		state.snoozeTimer:stop()
		state.snoozeTimer = nil
	end

	local deadline = hs.settings.get(config.quietOnWifi.snoozeSetting)
	if type(deadline) ~= "number" then return false end

	local remaining = deadline - hs.timer.secondsSinceEpoch()
	if remaining <= 0 then
		hs.settings.clear(config.quietOnWifi.snoozeSetting)
		return false
	end

	state.snoozeTimer = hs.timer.doAfter(remaining, function()
		state.snoozeTimer = nil
		quietOutputOnWifi()
	end)
	return true
end

local function finishPendingQuiet(pending)
	if state.pendingQuiet ~= pending then return end
	-- alwaysPresent requests presentation, but presented() still reports the
	-- Notification Center's original decision, not whether the banner appeared.
	-- Require successful delivery rather than that advisory presentation flag.
	local delivered = pending.notification:delivered()
	cancelPendingQuiet()
	if not delivered then
		print("Audio Device: skipped quieting because macOS did not confirm notification delivery")
		return
	end

	local device = quietOutputDevice()
	if device == nil then return end
	if device:setVolume(config.quietOnWifi.volume) == false then
		notify("Audio Device", "无法将内置扬声器音量归零，请手动检查。")
	end
end

quietOutputOnWifi = function()
	if scheduleSnoozeCheck() then
		cancelPendingQuiet()
		return
	end

	if quietOutputDevice() == nil then
		cancelPendingQuiet()
		return
	end

	if state.pendingQuiet ~= nil then
		if hs.timer.secondsSinceEpoch() >= state.pendingQuiet.deadline then
			finishPendingQuiet(state.pendingQuiet)
		end
		return
	end

	local pending = { deadline = hs.timer.secondsSinceEpoch() + config.quietOnWifi.graceSeconds }
	state.pendingQuiet = pending
	local durations = { ["30 min"] = 30 * 60, ["1 hour"] = 60 * 60 }
	pending.notification = hs.notify.new(function(notification)
		if state.pendingQuiet ~= pending then return end
		if hs.timer.secondsSinceEpoch() >= pending.deadline then
			finishPendingQuiet(pending)
			return
		end

		local activation = notification:activationType()
		local duration
		if activation == hs.notify.activationTypes.actionButtonClicked then
			duration = 10 * 60
		elseif activation == hs.notify.activationTypes.additionalActionClicked then
			duration = durations[notification:additionalActivationAction()]
		end
		if duration == nil then return end

		local device = quietOutputDevice()
		cancelPendingQuiet()
		if device == nil then return end

		hs.settings.set(config.quietOnWifi.snoozeSetting, hs.timer.secondsSinceEpoch() + duration)
		scheduleSnoozeCheck()
	end, {
		title = "内置扬声器即将静音",
		informativeText = "当前连接 " .. config.quietOnWifi.ssid .. "，15 秒后音量归零。需要外放请选择允许使用的时长。",
		hasActionButton = true,
		actionButtonTitle = "10 min",
		additionalActions = { "30 min", "1 hour" },
		alwaysShowAdditionalActions = true,
		-- Request native presentation even when Hammerspoon is frontmost.
		-- macOS notification permissions and Focus can still suppress it.
		alwaysPresent = true,
		autoWithdraw = false,
		withdrawAfter = 0,
	})
	pending.notification:send()
	pending.timer = hs.timer.doAfter(config.quietOnWifi.graceSeconds, function() finishPendingQuiet(pending) end)
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

local function currentOutputUID()
	local device = hs.audiodevice.defaultOutputDevice()
	return device and device:uid() or nil
end

local function handleWifiChange()
	local ssid = currentSSID()
	if ssid == state.lastSSID then return end

	state.lastSSID = ssid
	quietOutputOnWifi()
end

local function handleAudioDeviceChange()
	local uid = currentOutputUID()
	if uid ~= state.lastOutputUID then
		state.lastOutputUID = uid
		quietOutputOnWifi()
	end
	selectPreferredInput()
end

function M.setup()
	-- Capture the initial environment before starting watchers so duplicate
	-- events and input-device changes do not restart the quiet countdown.
	if not state.initialized then
		state.lastSSID = currentSSID()
		state.lastOutputUID = currentOutputUID()
		state.initialized = true
	end

	if state.wifiWatcher == nil then
		state.wifiWatcher = hs.wifi.watcher.new(handleWifiChange)
		state.wifiWatcher:start()
	end

	if not state.audioWatcherStarted then
		hs.audiodevice.watcher.setCallback(handleAudioDeviceChange)
		hs.audiodevice.watcher.start()
		state.audioWatcherStarted = true
	end

	if state.wakeWatcher == nil then
		state.wakeWatcher = hs.caffeinate.watcher.new(function(event)
			if event == hs.caffeinate.watcher.systemDidWake then quietOutputOnWifi() end
		end)
		state.wakeWatcher:start()
	end

	quietOutputOnWifi()
	selectPreferredInput()
end

return M
