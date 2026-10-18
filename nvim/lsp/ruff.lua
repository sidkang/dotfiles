local root_markers = { "pyproject.toml", "ruff.toml", ".ruff.toml", ".git" }

return {
	root_dir = function(bufnr, on_dir)
		if vim.bo[bufnr].buftype ~= "" or vim.api.nvim_buf_get_name(bufnr) == "" then
			return
		end
		on_dir(vim.fs.root(bufnr, root_markers) or vim.fn.getcwd())
	end,
	on_attach = function(client, _)
		client.server_capabilities.hoverProvider = false
	end,
	before_init = function(_, config)
		local python = vim.env.UV_PYTHON
		if not python or python == "" then
			return
		end
		if not config.settings then
			config.settings = { python = {} }
		end
		if not config.settings.python then
			config.settings.python = {}
		end
		config.settings.python.pythonPath = python
	end,
	init_options = {
		settings = {
			args = {},
		},
	},
}
