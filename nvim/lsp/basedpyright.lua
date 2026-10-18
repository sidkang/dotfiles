local M = {}

local root_markers = { "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", ".git" }

function M.config()
	return {
		root_dir = function(bufnr, on_dir)
			if vim.bo[bufnr].buftype ~= "" or vim.api.nvim_buf_get_name(bufnr) == "" then
				return
			end
			on_dir(vim.fs.root(bufnr, root_markers) or vim.fn.getcwd())
		end,
		before_init = function(_, config)
			local python = vim.env.UV_PYTHON
			if not python or python == "" then
				return
			end
			if not config.settings then
				config.settings = {}
			end
			if not config.settings.python then
				config.settings.python = {}
			end
			config.settings.python.pythonPath = python
		end,
		settings = {
			basedpyright = {
				analysis = {
					-- typeCheckingMode = "basic",
					typeCheckingMode = "standard", --all
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
end

return M.config()
