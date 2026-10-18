vim.api.nvim_create_autocmd("BufWritePre", {
	buffer = 0,
	callback = function()
		local save_cursor = vim.fn.getpos(".")
		vim.cmd([[%s/\s\+$//e]])
		vim.fn.setpos(".", save_cursor)
	end,
})
