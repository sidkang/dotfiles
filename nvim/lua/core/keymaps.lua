-- local map = function(mode, keys, func, opts)
-- 	local options = { silent = true }
-- 	if type(opts) == "string" then
-- 		options.desc = opts
-- 	else
-- 		opts = opts or {}
-- 		options.desc = opts.desc or ""
-- 		options = { unpack(options), unpack(opts) }
-- 	end
-- 	vim.keymap.set(mode, keys, func, options)
-- end

local map = function(mode, keys, func, opts)
	local options = { silent = true }

	if type(opts) == "string" then
		options.desc = opts
	else
		opts = opts or {}
		options = vim.tbl_extend("force", options, opts)
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
map("n", "<C-Up>", ":resize -2<CR>", "Resize window up")
map("n", "<C-Down>", ":resize +2<CR>", "Resize window down")
map("n", "<C-Left>", ":vertical resize -2<CR>", "Resize window left")
map("n", "<C-Right>", ":vertical resize +2<CR>", "Resize window right")

-- Navigate buffers
map("n", "<S-l>", ":bnext<CR>", "Next buffer")
map("n", "<S-h>", ":bprevious<CR>", "Previous buffer")

-- Terminal Mappings
map("t", "<C-x>", "<C-\\><C-N>", "Exit terminal mode")
map("t", "<esc><esc>", "<c-\\><c-n>", "Enter Normal mode")
map("t", "<C-/>", "<cmd>close<CR>", "Close terminal window")

-- window
map("n", "<leader>wx", "<C-w>c", { desc = "Delete Window", remap = true })

map("n", "<leader>wd", ":bp<bar>bd#<CR>", { desc = "Delete Buffer", remap = true })
map("n", "<leader>wv", "<C-w>v", { desc = "Split window right", remap = true })
map("n", "<leader>ws", "<C-w>s", { desc = "Split window below", remap = true })
map("n", "<leader>wh", "<C-w>h", { desc = "Go to left window", remap = true })
map("n", "<leader>wj", "<C-w>j", { desc = "Go to lower window", remap = true })
map("n", "<leader>wk", "<C-w>k", { desc = "Go to upper window", remap = true })
map("n", "<leader>wl", "<C-w>l", { desc = "Go to right window", remap = true })
map("n", "<leader>w=", "<C-w>=", { desc = "Equalize window sizes", remap = true })

-- toggles
map("n", "<leader>ud", function()
	local enabled = vim.diagnostic.is_enabled()
	vim.diagnostic.enable(not enabled)
end, "[U]I Toggle [D]iagnostics")
map("n", "<leader>uv", function()
	local current = vim.diagnostic.config().virtual_text
	local enabled = current == nil or current == true or type(current) == "table"
	vim.diagnostic.config({ virtual_text = not enabled })
end, "[U]I Toggle Diagnostic [V]irtual Text")
map("n", "<leader>uV", function()
	local current = vim.diagnostic.config().virtual_text
	local error_only = type(current) == "table" and current.severity and current.severity.min == vim.diagnostic.severity.ERROR and current.severity.max == vim.diagnostic.severity.ERROR
	if error_only then
		vim.diagnostic.config({ virtual_text = false })
	else
		vim.diagnostic.config({
			virtual_text = {
				severity = {
					min = vim.diagnostic.severity.ERROR,
					max = vim.diagnostic.severity.ERROR,
				},
			},
		})
	end
end, "[U]I Toggle Error [V]irtual Text")

map("n", "<leader>uw", function() vim.wo.wrap = not vim.wo.wrap end, "[U]I Toggle [W]rap")
map("n", "<leader>us", function() vim.wo.spell = not vim.wo.spell end, "[U]I Toggle [S]pell")
map("n", "<leader>ul", function()
	local enabled = vim.wo.number or vim.wo.relativenumber
	vim.wo.number = not enabled
	vim.wo.relativenumber = not enabled
end, "[U]I Toggle [L]ine Numbers")

local jump_diagnostic = function(count, severity)
	vim.diagnostic.jump({
		count = count,
		severity = severity,
		on_jump = function() vim.diagnostic.open_float(nil, { scope = "cursor", focus = false }) end,
	})
end

map("n", "[d", function() jump_diagnostic(-1) end, "Prev diagnostic")
map("n", "]d", function() jump_diagnostic(1) end, "Next diagnostic")
map("n", "[e", function() jump_diagnostic(-1, vim.diagnostic.severity.ERROR) end, "Go to previous [E]rror")
map("n", "]e", function() jump_diagnostic(1, vim.diagnostic.severity.ERROR) end, "Go to next [E]rror")

-- REPL
-- move cursor
-- local keymap = function(lhs, side, textobj_id, ai_type, search_method, desc)
-- 	for _, mode in ipairs { "n", "x", "o" } do
-- 		vim.keymap.set(mode, lhs, function()
-- 			-- MiniAi.move_cursor(side, ai_type, textobj_id, { search_method = search_method })
-- 			require("mini.ai").move_cursor(side, ai_type, textobj_id, { search_method = search_method })
-- 		end, { desc = desc })
-- 	end
-- end
--
-- keymap("[r", "left", "r", "i", "prev", "Code_cell start")
-- keymap("]r", "left", "r", "i", "next", "Code_cell start")
