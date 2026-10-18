local M = {}

local function cleanPasteboard()
	local pb = hs.pasteboard.contentTypes()
	local contains = hs.fnutils.contains
	if contains(pb, "com.apple.webarchive") and contains(pb, "public.rtf") then
		hs.pasteboard.setContents(hs.pasteboard.getContents())
	end
end

local messagesWindowFilter = hs.window.filter.new(false):setAppFilter("Messages")
messagesWindowFilter:subscribe(hs.window.filter.windowFocused, cleanPasteboard)

local wf = hs.window.filter.new(function(win)
	local fw = hs.window.focusedWindow()
	return (win:isStandard() and win:application() == fw:application() and win:screen() == fw:screen())
end)

return M
