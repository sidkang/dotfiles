vim.g.mapleader = " "
vim.g.maplocalleader = ","

vim.opt.number = true -- Make line numbers default
vim.opt.numberwidth = 2
vim.opt.relativenumber = true
-- vim.opt.statuscolumn = "%=%{v:virtnum < 1 ? (v:relnum ? v:relnum : v:lnum < 10 ? v:lnum . '  ' : v:lnum) : ''}%=%s"
vim.o.ruler = false

vim.opt.nrformats:remove("octal") -- Disable octal number parsing.

vim.opt.shiftround = true -- Round indent
vim.opt.shiftwidth = 2 -- Size of an indent
vim.opt.expandtab = true
vim.opt.tabstop = 2 -- Number of spaces tabs count for
vim.opt.softtabstop = 2
vim.opt.breakindent = true -- Enable break indent

-- vim.opt.fillchars = [[eob: ,fold: ,foldopen:󰛲,foldsep:│,foldclose:󰜄,vert:│,horiz:─,horizup:┴,horizdown:┬,vertleft:┤,vertright:├,verthoriz:┼]]
-- vim.opt.fillchars = "eob: ,fold: ,foldopen:󰛲,foldsep:│,foldclose:󰜄"
-- vim.opt.fillchars = "eob: ,fold: ,foldopen:󰛲,foldsep:│,foldclose:󰜄,foldinner: "
-- vim.opt.foldcolumn = "1"

-- Enable mouse support.
vim.o.mouse = "a"

-- Hide mode, since it is usually shown in the statusline.
vim.o.showmode = false

-- Enable remote clipboard to host
if vim.env.SSH_TTY or vim.env.SSH_CONNECTION then vim.g.clipboard = "osc52" end

-- Sync with the system clipboard after startup.
vim.schedule(function() vim.o.clipboard = "unnamedplus" end)

vim.opt.undofile = true -- Save undo history

vim.opt.ignorecase = true
vim.opt.smartcase = true -- Case-insensitive searching UNLESS \C or one or more capital letters in the search term

vim.opt.signcolumn = "yes" -- Keep signcolumn on by default

vim.opt.updatetime = 250 -- Decrease update time
vim.opt.timeoutlen = 500 -- Decrease mapped sequence wait time, displays which-key popup sooner

-- Configure how new splits should be opened
vim.opt.splitright = true
vim.opt.splitbelow = true

vim.opt.list = false
vim.opt.listchars = { tab = "» ", trail = "·", nbsp = "␣" }
vim.opt.cursorline = true
vim.opt.cursorlineopt = "line"

vim.opt.inccommand = "split" -- Preview substitutions live, as you type!
vim.opt.scrolloff = 10 -- Minimal number of screen lines to keep above and below the cursor

vim.opt.winborder = "rounded"

vim.opt.cmdheight = 1
vim.opt.termguicolors = true
vim.opt.wrap = false -- no pause the listing continues until finished.

vim.g.python3_host_prog = vim.fn.expand("$CENTRAL_VENV_DIR/nvim/bin/python")
vim.g.loaded_node_provider = 0
vim.g.loaded_perl_provider = 0
vim.g.loaded_ruby_provider = 0

vim.o.exrc = true -- 开启权限
