local M = {}

local state = {
	timers = {},
}

local schedule = {
	{ time = "12:00", title = "Daily Tasks", message = "Lunch time." },
}

local function notify(title, message)
	hs.notify.new({ title = title, informativeText = message }):send()
end

local function registerReminder(item)
	return hs.timer.doAt(item.time, "1d", function()
		notify(item.title, item.message)
	end)
end

function M.setup()
	if #state.timers > 0 then return end

	for _, item in ipairs(schedule) do
		state.timers[#state.timers + 1] = registerReminder(item)
	end
end

return M
