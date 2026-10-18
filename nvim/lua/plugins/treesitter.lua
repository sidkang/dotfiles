return { -- Highlight, edit, and navigate code
	"nvim-treesitter/nvim-treesitter",
	lazy = false,
	build = ":TSUpdate",
	dependencies = {
		{
			"nvim-treesitter/nvim-treesitter-textobjects",
			branch = "main",
			config = function()
				local select = require("nvim-treesitter-textobjects.select")
				local move = require("nvim-treesitter-textobjects.move")
				local repeatable_move = require("nvim-treesitter-textobjects.repeatable_move")

				require("nvim-treesitter-textobjects").setup({
					select = {
						lookahead = true,
						include_surrounding_whitespace = true,
					},
					move = {
						set_jumps = true,
					},
				})

				for key, query in pairs({
					["aa"] = "@parameter.outer",
					["ia"] = "@parameter.inner",
					["af"] = "@function.outer",
					["if"] = "@function.inner",
					["ac"] = "@class.outer",
					["ic"] = "@class.inner",
					["aj"] = "@conditional.outer",
					["ij"] = "@conditional.inner",
					["al"] = "@loop.outer",
					["il"] = "@loop.inner",
				}) do
					vim.keymap.set({ "x", "o" }, key, function()
						select.select_textobject(query, "textobjects")
					end)
				end

				for key, query in pairs({
					["]a"] = "@parameter.outer",
					["]f"] = "@function.outer",
					["]c"] = "@class.outer",
					["]j"] = "@conditional.outer",
					["]l"] = "@loop.outer",
				}) do
					vim.keymap.set({ "n", "x", "o" }, key, function()
						move.goto_next_start(query, "textobjects")
					end)
				end

				for key, query in pairs({
					["[a"] = "@parameter.outer",
					["[f"] = "@function.outer",
					["[c"] = "@class.outer",
					["[j"] = "@conditional.outer",
					["[l"] = "@loop.outer",
				}) do
					vim.keymap.set({ "n", "x", "o" }, key, function()
						move.goto_previous_start(query, "textobjects")
					end)
				end

				vim.keymap.set({ "n", "x", "o" }, ";", repeatable_move.repeat_last_move, { desc = "Repeat last move" })
				vim.keymap.set(
					{ "n", "x", "o" },
					",",
					repeatable_move.repeat_last_move_opposite,
					{ desc = "Repeat last move opposite" }
				)

				vim.keymap.set(
					{ "n", "x", "o" },
					"f",
					repeatable_move.builtin_f_expr,
					{ expr = true, desc = "Move to next char" }
				)
				vim.keymap.set(
					{ "n", "x", "o" },
					"F",
					repeatable_move.builtin_F_expr,
					{ expr = true, desc = "Move to prev char" }
				)
				vim.keymap.set(
					{ "n", "x", "o" },
					"t",
					repeatable_move.builtin_t_expr,
					{ expr = true, desc = "Move before next char" }
				)
				vim.keymap.set(
					{ "n", "x", "o" },
					"T",
					repeatable_move.builtin_T_expr,
					{ expr = true, desc = "Move before prev char" }
				)
			end,
		},
	},
	keys = {
		{
			"<leader>uT",
			function()
				local buf = vim.api.nvim_get_current_buf()
				if vim.treesitter.highlighter.active[buf] then
					vim.treesitter.stop(buf)
				else
					vim.treesitter.start(buf)
				end
			end,
			desc = "[U]I Toggle [T]reesitter",
		},
	},
	config = function()
		local ensure_installed = {
			"bash",
			"c",
			"diff",
			"html",
			"lua",
			"luadoc",
			"markdown",
			"markdown_inline",
			"ninja",
			"python",
			"query",
			"vim",
			"vimdoc",
			"yaml",
		}
		require("nvim-treesitter").install(ensure_installed)
	end,
}
