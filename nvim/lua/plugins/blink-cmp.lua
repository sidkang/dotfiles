return {
	"saghen/blink.cmp",
	event = "VimEnter",
	version = "1.*",
	dependencies = {
		"echasnovski/mini.nvim",
		{
			"saghen/blink.compat",
			version = "*",
			lazy = true,
			opts = {},
		},
	},
	---@module 'blink.cmp'
	---@type blink.cmp.Config
	opts = {
		keymap = {
			preset = "default",
		},
		appearance = {
			nerd_font_variant = "mono",
		},
		cmdline = {
			keymap = { preset = "inherit" },
			completion = { menu = { auto_show = true } },
		},
		completion = {
			documentation = { auto_show = false, auto_show_delay_ms = 500 },
			menu = {
				draw = {
					columns = {
						{ "kind_icon" },
						{ "label" },
						{ "source_name" },
					},
				},
			},
		},
		sources = {
			default = { "lsp", "path", "snippets" },
		},
		fuzzy = { implementation = "lua" },
		signature = { enabled = true },
	},
}
