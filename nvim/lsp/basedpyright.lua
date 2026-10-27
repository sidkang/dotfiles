return {
	root_dir = require("utils.lsp").root_dir({ "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", ".git" }),
	before_init = function(_, config)
		local python = vim.env.UV_PYTHON
		if python and python ~= "" then
			config.settings = vim.tbl_deep_extend("force", config.settings or {}, { python = { pythonPath = python } })
		end
	end,
	settings = {
		basedpyright = {
			analysis = {
				typeCheckingMode = "standard",
				autoImportCompletions = true,
				diagnosticSeverityOverrides = {
					reportGeneralTypeIssues = "none",
					reportIgnoreCommentWithoutRule = "none",
					reportMissingSuperCall = false,
					reportMissingTypeStubs = "none",
					reportOptionalMemberAccess = "none",
					reportOptionalSubscript = "none",
					reportPrivateImportUsage = "none",
					reportUnknownVariableType = "none",
					reportUnusedFunction = "information",
					reportUnusedImport = "information",
					reportUnusedVariable = "information",
				},
			},
		},
	},
}
