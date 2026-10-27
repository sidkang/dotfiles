-- Read-only Jujutsu helpers. Every call uses --ignore-working-copy so Neovim never snapshots or locks the repo.
local M = {}

local labels = {} ---@type table<string, string>
local pending = {} ---@type table<string, boolean>
local roots = {} ---@type table<integer, string|false>

---@param root string
---@param args string[]
---@param on_done fun(result: vim.SystemCompleted)
function M.run(root, args, on_done)
	local cmd = vim.list_extend({ "jj", "--no-pager", "--ignore-working-copy", "--color=never", "-R", root }, args)
	vim.system(cmd, { text = true }, vim.schedule_wrap(on_done))
end

---@param buf? integer
---@return string?
function M.root(buf)
	buf = buf ~= nil and buf ~= 0 and buf or vim.api.nvim_get_current_buf()
	if roots[buf] == nil then
		local name = vim.api.nvim_buf_get_name(buf)
		roots[buf] = vim.bo[buf].buftype == "" and vim.fs.root(name ~= "" and name or vim.uv.cwd(), ".jj") or false
	end
	return roots[buf] or nil
end

---@param root string
function M.refresh(root)
	if pending[root] then return end
	pending[root] = true
	local template = [[change_id.shortest(4) ++ if(bookmarks, " " ++ bookmarks.join(" "))]]
	M.run(root, { "log", "-r", "@", "--no-graph", "-T", template }, function(result)
		pending[root] = nil
		local label = result.code == 0 and vim.trim(result.stdout) or ""
		if labels[root] ~= label then
			labels[root] = label
			vim.cmd.redrawstatus()
		end
	end)
end

--- Cached "<change id> <bookmarks>" of @ for the buffer's repo; nil outside jj repos.
---@param buf? integer
---@return string?
function M.label(buf)
	local root = M.root(buf)
	if not root then return end
	if labels[root] == nil then
		labels[root] = ""
		M.refresh(root)
	end
	return labels[root] ~= "" and labels[root] or nil
end

vim.api.nvim_create_autocmd({ "BufFilePost", "BufDelete", "BufWipeout" }, {
	group = vim.api.nvim_create_augroup("user-jj-root", { clear = true }),
	callback = function(args) roots[args.buf] = nil end,
})

vim.api.nvim_create_autocmd({ "BufEnter", "FocusGained", "ShellCmdPost", "TermLeave", "TermClose" }, {
	group = vim.api.nvim_create_augroup("user-jj-label", { clear = true }),
	callback = function(args)
		local root = M.root(args.buf)
		if root then M.refresh(root) end
	end,
})

return M
