local space = {}
local spaces = require("hs.spaces")

space.MoveWindowToSpace = function(sp)
    -- move current window to the space sp
    local win = hs.window.focusedWindow()  -- current window
    local uuid = win:screen():spacesUUID() -- uuid for current screen
    local spaceID = spaces.layout()[uuid][sp] -- internal index for sp
    if spaces.layout()[uuid][sp] == spaces.activeSpace() then
        -- not current space
        hs.alert.show(hs.styledtext.new("Already in " .. sp .. " space.", {
            color = inDarkMode and { red = 0.8, blue = 0.8, green = 0.8 } or { red = 1, blue = 1, green = 1 },
            font = { name = "Menlo", size = 20 },
            strokeColor = { white = 1, alpha = 0 },
            fillColor = { white = 0.05, alpha = 0.75 },
            radius = 10,
        }))
    elseif spaces.layout()[uuid][sp] then
        -- move window
        hs.alert.show("Succeed.")
        spaces.moveWindowToSpace(win:id(), spaceID) -- move window to new space
        spaces.changeToSpace(spaceID)         -- follow window to new space
    else
        -- space id not exist
        hs.alert.show("Space " .. sp .. " unexisted.")
    end
end

space.MoveWindowToLorRSpace = function(sp)
    -- local spaces = require("hs.spaces")
    local win = hs.window.focusedWindow()    -- current window
    local uuid = win:screen():spacesUUID()   -- uuid for current screen
    local spaceID = spaces.layout()[uuid][sp] -- internal index for sp
    spaces.moveWindowToSpace(win:id(), spaceID) -- move window to new space
    spaces.changeToSpace(spaceID)            -- follow window to new space
end

return space

