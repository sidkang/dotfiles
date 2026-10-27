vim.filetype.add({
	extension = {
		bean = "beancount",
		list = "list",
	},
	filename = {
		["Caddyfile"] = "caddyfile",
	},
})

local group = vim.api.nvim_create_augroup("user-core", { clear = true })
local autocmd = function(event, opts)
	vim.api.nvim_create_autocmd(event, vim.tbl_extend("force", { group = group }, opts))
end

autocmd("FileType", {
	pattern = { "json", "list" },
	callback = function(args) vim.bo[args.buf].commentstring = "// %s" end,
})

autocmd("TextYankPost", {
	callback = function() vim.hl.on_yank() end,
})

autocmd("BufReadPost", {
	desc = "Restore last cursor position",
	callback = function(args)
		if vim.bo[args.buf].buftype ~= "" or vim.bo[args.buf].filetype:match("^git") or vim.bo[args.buf].filetype == "jjdescription" then return end
		local mark = vim.api.nvim_buf_get_mark(args.buf, '"')
		if mark[1] > 0 and mark[1] <= vim.api.nvim_buf_line_count(args.buf) then pcall(vim.api.nvim_win_set_cursor, 0, mark) end
	end,
})

autocmd({ "FocusGained", "TermClose", "TermLeave" }, {
	desc = "Pick up files changed outside Neovim",
	command = "silent! checktime",
})

autocmd("VimResized", {
	desc = "Keep splits equal after resizing the terminal",
	command = "tabdo wincmd =",
})

autocmd("BufWritePre", {
	desc = "Create missing parent directories",
	callback = function(args)
		if args.match:match("^%w%w+:[\\/][\\/]") then return end
		vim.fn.mkdir(vim.fs.dirname(args.match), "p")
	end,
})

-- macOS: switch to the English input source through Hammerspoon.
-- Only spawn when the source may have changed: always after Insert mode, in the
-- command line only after typing non-ASCII text or when focus came back.
if vim.uv.os_uname().sysname == "Darwin" and not (vim.env.SSH_TTY or vim.env.SSH_CONNECTION) then
	local en = false
	local switch_en = function()
		if en then return end
		en = true
		vim.system({ "open", "-g", "hammerspoon://switchIME?to=en" })
	end

	autocmd("InsertEnter", { callback = function() en = false end })
	autocmd("FocusGained", { callback = function() en = false end })
	autocmd("InsertLeave", { callback = switch_en })
	autocmd("CmdlineEnter", { callback = switch_en })
	autocmd("CmdlineLeave", {
		callback = function()
			if vim.fn.getcmdline():find("[\128-\255]") then en = false end
		end,
	})
end
