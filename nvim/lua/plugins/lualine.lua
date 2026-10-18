return {
	"nvim-lualine/lualine.nvim",
	dependencies = { "catppuccin/nvim" },
	config = function()
		local palette = require("catppuccin.palettes").get_palette("latte")

		local mode_colors = {
			n = palette.blue,
			i = palette.green,
			v = palette.sapphire,
			V = palette.sapphire,
			["\22"] = palette.sapphire,
			c = palette.peach,
			s = palette.mauve,
			S = palette.mauve,
			["\19"] = palette.mauve,
			R = palette.peach,
			r = palette.peach,
			["!"] = palette.pink,
			t = palette.pink,
		}

		-- TODO: Consider adding lightweight breadcrumbs with nvim-navic in winbar.
		local function mode_block()
			return {
				function()
					return " "
				end,
				padding = 0,
				color = function()
					local mode = vim.fn.mode(1):sub(1, 1)
					return { bg = mode_colors[mode] or palette.mauve }
				end,
			}
		end

		require("lualine").setup({
			options = {
				icons_enabled = true,
				theme = "auto",
				component_separators = { left = "", right = "" },
				section_separators = { left = "", right = "" },
				disabled_filetypes = {
					statusline = {},
					winbar = {},
				},
				ignore_focus = {},
				always_divide_middle = true,
				always_show_tabline = true,
				globalstatus = false,
				refresh = {
					statusline = 1000,
					tabline = 1000,
					winbar = 1000,
					refresh_time = 16, -- ~60fps
					events = {
						"WinEnter",
						"BufEnter",
						"BufWritePost",
						"SessionLoadPost",
						"FileChangedShellPost",
						"VimResized",
						"Filetype",
						"CursorMoved",
						"CursorMovedI",
						"ModeChanged",
					},
				},
			},
			sections = {
				lualine_a = {
					mode_block(),
				},
				lualine_b = { "branch", "diff", "diagnostics" },
				lualine_c = {
					{
						"filename",
						path = 0,
						color = function()
							if vim.bo.modified then
								return { fg = palette.text, gui = "bold" }
							end
							return { fg = palette.subtext0 }
						end,
						fmt = function(str)
							return str:gsub("^(.-) (%b[])$", "%1%2")
						end,
					},
					{
						"diagnostics",
						sources = { "nvim_diagnostic" },
						sections = { "error", "warn", "info", "hint" },
						symbols = {
							error = "󰅚 ",
							warn = "󰀪 ",
							info = "󰋽 ",
							hint = "󰌶 ",
						},
						diagnostics_color = {
							error = { fg = palette.red },
							warn = { fg = palette.yellow },
							info = { fg = palette.sky },
							hint = { fg = palette.teal },
						},
						colored = true,
						update_in_insert = false,
						always_visible = false,
					},
				},
				lualine_x = {
					{
						"lsp_status",
						icons_enabled = false,
						color = { fg = palette.lavender, gui = "bold" },
						symbols = {
							spinner = { "⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏" },
							done = "",
							separator = " ",
						},
						ignore_lsp = {},
						show_name = true,
						fmt = function(str)
							if str == "" then
								return ""
							end
							return " [" .. str .. "]"
						end,
					},
					"encoding",
					{
						"filetype",
						icons_enabled = false,
						fmt = function(str)
							return str:lower()
						end,
						color = { fg = palette.pink },
					},
				},
				lualine_y = {},
				lualine_z = { mode_block() },
			},
			inactive_sections = {
				lualine_a = {},
				lualine_b = {},
				lualine_c = { "filename" },
				lualine_x = { "location" },
				lualine_y = {},
				lualine_z = {},
			},
			tabline = {},
			winbar = {},
			inactive_winbar = {},
			extensions = {},
		})
	end,
}
