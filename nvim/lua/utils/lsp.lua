local M = {}

--- root_dir for servers that should also run on loose files: fall back to cwd.
---@param markers string[]
function M.root_dir(markers)
	return function(bufnr, on_dir)
		if vim.bo[bufnr].buftype ~= "" or vim.api.nvim_buf_get_name(bufnr) == "" then return end
		on_dir(vim.fs.root(bufnr, markers) or vim.fn.getcwd())
	end
end

return M
