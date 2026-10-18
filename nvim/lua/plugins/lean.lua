return {
	"Julian/lean.nvim",
	enabled = false,
	ft = "lean",
	dependencies = {
		"neovim/nvim-lspconfig",
		"nvim-lua/plenary.nvim",
	},
	opts = {
		mappings = true,
		goal_markers = {
			unsolved = "",
			accomplished = "󰸞 ",
		},
	},
}
