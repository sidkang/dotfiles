return {
	"saghen/blink.pairs",
	version = "*", -- (recommended) only required with prebuilt binaries
	build = function()
		require("blink.pairs").download():pwait(60000)
	end,

	-- download prebuilt binaries from github releases
	dependencies = "saghen/blink.lib",

	--- @module 'blink.pairs'
	--- @type blink.pairs.Config
	opts = {
		mappings = {
			enabled = true,
			cmdline = true,
			disabled_filetypes = {},
			pairs = {},
		},
		highlights = {
			enabled = true,
			cmdline = true,
			groups = {
				"BlinkPairsOrange",
				"BlinkPairsPurple",
				"BlinkPairsBlue",
			},
			unmatched_group = "BlinkPairsUnmatched",

			matchparen = {
				enabled = true,
				cmdline = false,
				include_surrounding = false,
				group = "BlinkPairsMatchParen",
				priority = 250,
			},
		},
		debug = false,
	},
}
