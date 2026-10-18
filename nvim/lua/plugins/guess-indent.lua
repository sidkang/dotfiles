---@type LazySpec
return {
	"nmac427/guess-indent.nvim",
	event = { "BufReadPre", "BufNewFile" },
	opts = {
		auto_cmd = true,
		override_editorconfig = false,
		filetype_exclude = {
			"netrw",
			"tutor",
		},
		buftype_exclude = {
			"help",
			"nofile",
			"terminal",
			"prompt",
		},
	},
}
