local severity = vim.diagnostic.severity

vim.diagnostic.config({
	severity_sort = true,
	update_in_insert = false,
	virtual_text = false, -- toggled with <leader>uv / <leader>uV
	signs = {
		text = {
			[severity.ERROR] = "󰅚",
			[severity.WARN] = "󰀪",
			[severity.INFO] = "󰋽",
			[severity.HINT] = "󰌶",
		},
	},
	float = { source = "if_many" },
	jump = {
		on_jump = function(diagnostic, bufnr)
			if diagnostic then vim.diagnostic.open_float({ bufnr = bufnr, scope = "cursor", focus = false }) end
		end,
	},
})
