local filetypes = { "python", "sh" }

local function kitty_command(args)
	local command = { "kitty", "@" }
	if vim.env.KITTY_LISTEN_ON and vim.env.KITTY_LISTEN_ON ~= "" then
		vim.list_extend(command, { "--to", vim.env.KITTY_LISTEN_ON })
	end
	vim.list_extend(command, args)
	return command
end

local function get_kitty_tab_windows()
	local current_id = tonumber(vim.env.KITTY_WINDOW_ID)
	if not current_id then
		return
	end

	local result = vim.system(kitty_command({ "ls" }), { text = true }):wait()
	if result.code ~= 0 or result.stdout == "" then
		return
	end

	local ok, os_windows = pcall(vim.json.decode, result.stdout)
	if not ok then
		return
	end

	for _, os_window in ipairs(os_windows) do
		for _, tab in ipairs(os_window.tabs or {}) do
			local windows = tab.windows or {}
			for index, window in ipairs(windows) do
				if window.id == current_id then
					return windows, index
				end
			end
		end
	end
end

local function set_slime_target(bufnr, window)
	vim.b[bufnr].slime_config = {
		window_id = window.id,
		listen_on = vim.env.KITTY_LISTEN_ON or "",
	}
end

local function set_next_kitty_window(bufnr)
	local windows, current_index = get_kitty_tab_windows()
	if not windows or #windows < 2 then
		return false
	end

	set_slime_target(bufnr, windows[current_index % #windows + 1])
	return true
end

local function kitty_window_label(window)
	local title = window.title or ""
	local cwd = window.cwd or ""
	if cwd ~= "" then
		cwd = vim.fn.fnamemodify(cwd, ":~")
	end
	return table.concat(
		vim.tbl_filter(function(part)
			return part ~= ""
		end, { tostring(window.id), title, cwd }),
		"  "
	)
end

local function configure_kitty_target(bufnr)
	local windows, current_index = get_kitty_tab_windows()
	if not windows or #windows < 2 then
		vim.cmd.SlimeConfig()
		return
	end

	local targets = {}
	for index, window in ipairs(windows) do
		if index ~= current_index then
			table.insert(targets, window)
		end
	end

	if #targets == 1 then
		set_slime_target(bufnr, targets[1])
		vim.notify(("Slime target: kitty window %s"):format(targets[1].id))
		return
	end

	vim.ui.select(targets, {
		prompt = "Slime kitty target",
		format_item = kitty_window_label,
	}, function(choice)
		if not choice then
			return
		end
		set_slime_target(bufnr, choice)
		vim.notify(("Slime target: kitty window %s"):format(choice.id))
	end)
end

local function get_slime_target(bufnr)
	local config = vim.b[bufnr].slime_config
	if not config and set_next_kitty_window(bufnr) then
		config = vim.b[bufnr].slime_config
	end
	if config and config.window_id then
		return config
	end

	vim.notify("Slime target is not configured", vim.log.levels.WARN)
end

local function send_kitty_key(bufnr, key)
	local config = get_slime_target(bufnr)
	if not config then
		return
	end

	vim.system(kitty_command({ "send-key", "--match", ("id:%s"):format(config.window_id), key }))
end

local function send_cell(move_next)
	vim.fn["slime#send_cell"]()
	if move_next then
		vim.fn.search(vim.b.slime_cell_delimiter or "# %%", "W")
	end
end

local function setup_buffer(bufnr)
	vim.b[bufnr].slime_cell_delimiter = "# %%"
	set_next_kitty_window(bufnr)

	local map = function(mode, lhs, rhs, desc)
		vim.keymap.set(mode, lhs, rhs, { buffer = bufnr, desc = desc, remap = true, silent = true })
	end

	map("n", "<localleader>i", function()
		configure_kitty_target(bufnr)
	end, "Slime target")
	map("n", "<localleader>l", "<Plug>SlimeLineSend", "Send line")
	map("n", "<localleader>s", "<Plug>SlimeMotionSend", "Send motion")
	map("x", "<localleader>v", "<Plug>SlimeRegionSend", "Send selection")
	map("n", "<localleader>r", function()
		send_kitty_key(bufnr, "enter")
	end, "Send enter key")
	map("n", "<localleader>x", function()
		send_kitty_key(bufnr, "ctrl+c")
	end, "Send interrupt key")
	map("n", "<localleader>c", function()
		send_cell(false)
	end, "Send cell")
	map("n", "<localleader>n", function()
		send_cell(true)
	end, "Send cell and next")
end

return {
	"jpalardy/vim-slime",
	ft = filetypes,
	init = function()
		vim.g.slime_no_mappings = true
		vim.g.slime_target = "kitty"
		vim.g.slime_bracketed_paste = 1
	end,
	config = function()
		vim.api.nvim_create_autocmd("FileType", {
			pattern = filetypes,
			callback = function(args)
				setup_buffer(args.buf)
			end,
		})

		if vim.tbl_contains(filetypes, vim.bo.filetype) then
			setup_buffer(vim.api.nvim_get_current_buf())
		end
	end,
}
