---@type LazySpec
return {
	{
		"mason-org/mason.nvim",
		opts = {},
	},
	{
		"WhoIsSethDaniel/mason-tool-installer.nvim",
		dependencies = {
			"mason-org/mason.nvim",
		},
		opts = {
			ensure_installed = {
				"lua-language-server",
				"basedpyright",
				"ruff",
				"shfmt",
				"beanhub-cli",
				"yamlfmt",
				"stylua",
				"prettierd",
				"prettier",
				"kdlfmt",
				"cljfmt",
				-- Below use homebrew ones instead
				-- "joker",
			},
		},
	},
}
