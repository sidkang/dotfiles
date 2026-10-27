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
				"kdlfmt",
				"cljfmt",
				"beancount-language-server",
				"fish-lsp",
				"bash-language-server",
				"shellcheck",
				"yaml-language-server",
				"json-lsp",
				-- taplo, prettier, caddy and joker come from nvim/Brewfile
			},
		},
	},
}
