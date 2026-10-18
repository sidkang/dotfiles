local M = {}

local caffeine = hs.menubar.new()
local function setCaffeineDisplay(state)
	if state then
		M.caffeine:setTitle("AWAKE")
	else
		M.caffeine:setTitle("SLEEPY")
	end
end

local function caffeineClicked()
	setCaffeineDisplay(hs.caffeinate.toggle("displayIdle"))
end

M.setup = function()
	caffeine:setClickCallback(caffeineClicked)
	setCaffeineDisplay(hs.caffeinate.get("displayIdle"))
end

return M
