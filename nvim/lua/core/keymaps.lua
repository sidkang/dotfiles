local map = function(mode, keys, func, opts)
	local options = { silent = true }

	if type(opts) == "string" then
		options.desc = opts
	else
		options = vim.tbl_extend("force", options, opts or {})
	end

	vim.keymap.set(mode, keys, func, options)
end

map("i", "<C-h>", "<nop>", "Disable insert Ctrl-h")
map("i", "<C-l>", "<nop>", "Disable insert Ctrl-l")

map("n", "<Esc><Esc>", "<cmd>nohlsearch<CR>", "Clear search highlight")

-- better indenting
map("v", "<", "<gv", "Indent left and reselect")
map("v", ">", ">gv", "Indent right and reselect")

-- paste over visual selection without replacing the yank register
map("x", "p", '"_dP', "Paste without yanking replaced text")

-- resize window
map("n", "<C-Up>", "<cmd>resize -2<CR>", "Resize window up")
map("n", "<C-Down>", "<cmd>resize +2<CR>", "Resize window down")
map("n", "<C-Left>", "<cmd>vertical resize -2<CR>", "Resize window left")
map("n", "<C-Right>", "<cmd>vertical resize +2<CR>", "Resize window right")

-- Navigate buffers
map("n", "<S-l>", "<cmd>bnext<CR>", "Next buffer")
map("n", "<S-h>", "<cmd>bprevious<CR>", "Previous buffer")

-- Terminal Mappings
map("t", "<C-x>", "<C-\\><C-N>", "Exit terminal mode")
map("t", "<esc><esc>", "<c-\\><c-n>", "Enter Normal mode")
map("t", "<C-/>", "<cmd>close<CR>", "Close terminal window")

-- window / buffer
map("n", "<leader>wx", "<cmd>wincmd c<CR>", "Delete Window")
map("n", "<leader>wd", function() require("mini.bufremove").delete(0) end, "Delete Buffer")
map("n", "<leader>wD", function() require("mini.bufremove").delete(0, true) end, "Delete Buffer (force)")
map("n", "<leader>wv", "<cmd>wincmd v<CR>", "Split window right")
map("n", "<leader>ws", "<cmd>wincmd s<CR>", "Split window below")
map("n", "<leader>wh", "<cmd>wincmd h<CR>", "Go to left window")
map("n", "<leader>wj", "<cmd>wincmd j<CR>", "Go to lower window")
map("n", "<leader>wk", "<cmd>wincmd k<CR>", "Go to upper window")
map("n", "<leader>wl", "<cmd>wincmd l<CR>", "Go to right window")
map("n", "<leader>w=", "<cmd>wincmd =<CR>", "Equalize window sizes")

-- toggles
map("n", "<leader>ud", function() vim.diagnostic.enable(not vim.diagnostic.is_enabled()) end, "[U]I Toggle [D]iagnostics")
map("n", "<leader>uv", function()
	vim.diagnostic.config({ virtual_text = not vim.diagnostic.config().virtual_text })
end, "[U]I Toggle Diagnostic [V]irtual Text")
map("n", "<leader>uV", function()
	local current = vim.diagnostic.config().virtual_text
	local errors_only = type(current) == "table" and current.severity == vim.diagnostic.severity.ERROR
	vim.diagnostic.config({ virtual_text = not errors_only and { severity = vim.diagnostic.severity.ERROR } or false })
end, "[U]I Toggle Error [V]irtual Text")

map("n", "<leader>uw", function() vim.wo.wrap = not vim.wo.wrap end, "[U]I Toggle [W]rap")
map("n", "<leader>us", function() vim.wo.spell = not vim.wo.spell end, "[U]I Toggle [S]pell")
map("n", "<leader>ul", function()
	local enabled = vim.wo.number or vim.wo.relativenumber
	vim.wo.number = not enabled
	vim.wo.relativenumber = not enabled
end, "[U]I Toggle [L]ine Numbers")

-- [d / ]d are Neovim defaults; on_jump (core.diagnostics) opens the float
map("n", "[e", function() vim.diagnostic.jump({ count = -1, severity = vim.diagnostic.severity.ERROR }) end, "Go to previous [E]rror")
map("n", "]e", function() vim.diagnostic.jump({ count = 1, severity = vim.diagnostic.severity.ERROR }) end, "Go to next [E]rror")
