---@type MiniFilesModule
local mini_files = require("config.mini-files")
local mini_clue = require("config.mini-clue")
local mini_diff = require("config.mini-diff")
local mini_pick = require("config.mini-pick")

---@type LazySpec
return {
	"echasnovski/mini.nvim",
	version = "*",
	event = "VimEnter",
	keys = vim.list_extend(vim.list_extend(mini_files.keys, mini_diff.keys), mini_pick.keys),
	config = function()
		local mini_ai = require("mini.ai")
		local gen_ai_spec = mini_ai.gen_spec

		require("mini.notify").setup({
			window = {
				config = {
					border = "rounded",
				},
				winblend = 0,
			},
		})
		vim.notify = require("mini.notify").make_notify()

		mini_clue.setup()
		mini_diff.setup()
		mini_files.setup()
		mini_pick.setup()
		mini_ai.setup({
			custom_textobjects = {
				a = false,
				f = false,
				o = gen_ai_spec.treesitter({
					a = { "@block.outer", "@conditional.outer", "@loop.outer" },
					i = { "@block.inner", "@conditional.inner", "@loop.inner" },
				}),
				C = gen_ai_spec.treesitter({
					a = "@comment.outer",
					i = "@comment.inner",
				}),
			},
			mappings = {
				around = "a",
				inside = "i",
				around_next = "",
				inside_next = "",
				around_last = "",
				inside_last = "",
				goto_left = "g[",
				goto_right = "g]",
			},
			n_lines = 500,
			search_method = "cover_or_next",
		})
		require("mini.splitjoin").setup()
	end,
}
