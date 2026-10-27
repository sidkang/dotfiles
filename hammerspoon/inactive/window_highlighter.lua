hs.application.enableSpotlightForNameSearches(true)
hs.window.highlight.ui.overlay = true
-- {redN,greenN,blueN[,alphaN]} - if omitted alphaN defaults to 1.0
-- hs.window.highlight.ui.overlayColor = { 0, 0, 0, 0.001 }
local colors = {
	color_set = {
		maroon = { 230, 69, 83 },
		flamingo = { 221, 120, 120 },
		rosewater = { 220, 138, 120 },
		peach = { 254, 100, 11 },
		sky = { 4, 165, 229 },
		sapphire = { 32, 159, 181 },
		green = { 64, 160, 43 },
		lavender = { 114, 135, 253 },
		mauve = { 136, 57, 239 },
		yellow = { 223, 142, 29 },
	},
}
colors.transform = function(rgb, alpha)
	rgb = hs.fnutils.map(rgb, function(ele)
		return ele / 255
	end)
	return hs.fnutils.concat(rgb, { alpha })
end

colors.color = function(color, alpha)
	return colors.transform(colors.color_set[color], alpha)
end

-- hs.window.highlight.ui.overlayColor = { 0.2, 0.05, 0, 0.05 }
hs.window.highlight.ui.overlayColor = colors.color("yellow", 0.03)

hs.window.highlight.ui.frameWidth = 0
-- hs.window.highlight.ui.frameColor = { 0, 1, 0, 0.5 }
hs.window.highlight.ui.frameColor = colors.color("maroon", 0.35)
-- hs.window.highlight.ui.frameColor = { 23 / 255, 146 / 255, 153 / 255, 0.8 }

hs.window.highlight.ui.flashDuration = 0
hs.window.highlight.ui.windowShownFlashColor = { 0, 1, 0, 0.8 }

-- hs.window.highlight.start()
-- hs.window.highlight.stop()
