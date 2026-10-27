---@type MiniFilesModule
local mini_files = require("config.mini-files")
local mini_clue = require("config.mini-clue")
local mini_diff = require("config.mini-diff")
local mini_git = require("config.mini-git")
local mini_statusline = require("config.mini-statusline")
local mini_pick = require("config.mini-pick")

---@type LazySpec
return {
	"echasnovski/mini.nvim",
	version = "*",
	event = "VimEnter",
	keys = vim.iter({ mini_files.keys, mini_diff.keys, mini_git.keys, mini_pick.keys }):flatten(1):totable(),
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

		require("mini.icons").setup()
		mini_clue.setup()
		mini_git.setup()
		mini_diff.setup()
		mini_statusline.setup()
		require("mini.bufremove").setup()
		mini_files.setup()
		mini_pick.setup()
		mini_ai.setup({
			custom_textobjects = {
				a = gen_ai_spec.treesitter({ a = "@parameter.outer", i = "@parameter.inner" }),
				f = gen_ai_spec.treesitter({ a = "@function.outer", i = "@function.inner" }),
				c = gen_ai_spec.treesitter({ a = "@class.outer", i = "@class.inner" }),
				j = gen_ai_spec.treesitter({ a = "@conditional.outer", i = "@conditional.inner" }),
				l = gen_ai_spec.treesitter({ a = "@loop.outer", i = "@loop.inner" }),
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
		require("mini.surround").setup({
			mappings = {
				add = "gsa",
				delete = "gsd",
				replace = "gsr",
				find = "gsf",
				find_left = "gsF",
				highlight = "gsh",
				update_n_lines = "gsn",
			},
		})
	end,
}
