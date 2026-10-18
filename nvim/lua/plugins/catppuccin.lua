local color = require("utils.color")

return {
	{
		"catppuccin/nvim",
		priority = 1000, -- Make sure to load this before all the other start plugins.
		-- enabled = false,
		name = "catppuccin",
		opts = {
			flavour = "latte",
			background = {
				light = "latte",
				dark = "mocha",
			},
			transparent_background = true,
			float = {
				transparent = true, -- enable transparent floating windows
				solid = false, -- use solid styling for floating windows, see |winborder|
			},
			dim_inactive = {
				enabled = false, -- dims the background color of inactive window
				shade = "dark", -- if set to "dark", will use a darker shade for the background
				percentage = 0.15, -- percentage of the shade to apply to the inactive window
			},
			integrations = {
				mason = true,
				markdown = true,
				mini = true,
				native_lsp = {
					enabled = true,
					underlines = {
						errors = { "undercurl" },
						hints = { "undercurl" },
						warnings = { "undercurl" },
						information = { "undercurl" },
					},
				},
				semantic_tokens = true,
				treesitter = true,
			},

			custom_highlights = function(colors)
				local warm_yello = color.adjust(colors.yellow, -0.20, 0.10)

				return {
					MiniFilesCursorLine = { bg = colors.surface0, style = { "bold" } },
					WinSeparator = { fg = colors.overlay1, style = { "bold" } },
					VertSplit = { fg = colors.overlay1, style = { "bold" } },
					CursorLine = { bg = colors.surface0 },
					CursorLineNr = { fg = colors.sapphire, style = { "bold" } },

					DiagnosticError = { fg = colors.maroon },
					DiagnosticSignError = { fg = colors.maroon },
					DiagnosticVirtualTextError = { fg = colors.maroon },
					DiagnosticFloatingError = { fg = colors.maroon },
					DiagnosticUnderlineError = { sp = colors.maroon, style = { "undercurl" } },

					DiagnosticWarn = { fg = warm_yello },
					DiagnosticSignWarn = { fg = warm_yello },
					DiagnosticVirtualTextWarn = { fg = warm_yello },
					DiagnosticFloatingWarn = { fg = warm_yello },
					DiagnosticUnderlineWarn = { sp = warm_yello, style = { "undercurl" } },

					DiagnosticInfo = { fg = colors.sapphire },
					DiagnosticSignInfo = { fg = colors.sapphire },
					DiagnosticVirtualTextInfo = { fg = colors.sapphire },
					DiagnosticFloatingInfo = { fg = colors.sapphire },
					DiagnosticUnderlineInfo = { sp = colors.sapphire, style = { "undercurl" } },

					DiagnosticHint = { fg = colors.lavender },
					DiagnosticSignHint = { fg = colors.lavender },
					DiagnosticVirtualTextHint = { fg = colors.lavender },
					DiagnosticFloatingHint = { fg = colors.lavender },
					DiagnosticUnderlineHint = { sp = colors.lavender, style = { "undercurl" } },
					-- DropBarIconUISeparator = { fg = colors.teal, bg = colors.mantle },
					-- DropBarIconUISeparatorMenu = { fg = colors.teal, bg = colors.mantle },
					-- DropBarCurrentContext = { fg = colors.blue, bg = colors.mantle },
					-- DropBarFzfMatch = { fg = colors.yellow, bg = colors.mantle },
					-- DropBarHover = { fg = colors.blue, bg = colors.mantle },
					--
					-- TabLineSel = { bg = colors.pink },
					--
					-- -- mini.jump
					-- MiniJump = { fg = colors.base, bg = colors.green },
					-- -- mini.hipatterns
					-- MiniHipatternsTodo = { fg = colors.base, bg = colors.green },
					-- MiniHipatternsNote = { fg = colors.base, bg = colors.peach },
					-- MiniHipatternsWarn = { fg = colors.base, bg = colors.yellow },
					-- MiniHipatternsFix = { fg = colors.base, bg = colors.maroon },
					-- MiniHipatternsCell = { fg = colors.pink },
					-- -- mini.indentscope
					-- -- MiniIndentscopeSymbol = { fg = colors.surface2 },
					-- MiniIndentscopeSymbol = { fg = colors.pink },
					-- -- mini.diffsings
					-- MiniDiffSignAdd = { fg = colors.green },
					-- MiniDiffSignChange = { fg = colors.peach },
					-- MiniDiffSignDelete = { fg = colors.red },
				}
			end,
		},
		config = function(_, opts)
			require("catppuccin").setup(opts)
			vim.o.background = "light"
			vim.cmd.colorscheme("catppuccin")

			-- local palette = require("catppuccin.palettes").get_palette(opts.flavour)
			--
			-- for _, name in ipairs(vim.fn.getcompletion("DropBarKind", "highlight")) do
			-- 	if name:match("^DropBarKind") and not name:match("NC$") then
			-- 		vim.api.nvim_set_hl(0, name, { fg = palette.teal, bg = palette.mantle })
			-- 	end
			-- end
		end,
	},
}
