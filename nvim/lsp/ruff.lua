return {
	root_dir = require("utils.lsp").root_dir({ "pyproject.toml", "ruff.toml", ".ruff.toml", ".git" }),
	on_attach = function(client)
		client.server_capabilities.hoverProvider = false
	end,
}
