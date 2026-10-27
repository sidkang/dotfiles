vim.g.mapleader = " "
vim.g.maplocalleader = ","

local o = vim.o

o.number = true
o.numberwidth = 2
o.relativenumber = true
o.ruler = false
o.showmode = false -- mode is shown in the statusline
o.signcolumn = "yes"
o.cursorline = true
o.cursorlineopt = "line"
o.scrolloff = 10
o.winborder = "rounded"
o.cmdheight = 1
o.termguicolors = true
o.wrap = false
o.linebreak = true -- only matters when wrap is on

o.shiftround = true
o.shiftwidth = 2
o.tabstop = 2
o.softtabstop = 2
o.expandtab = true
o.breakindent = true

o.mouse = "a"
o.undofile = true
o.confirm = true -- ask instead of failing on unsaved buffers
o.updatetime = 250
o.timeoutlen = 500

o.ignorecase = true
o.smartcase = true
o.inccommand = "split"
o.grepprg = "rg --vimgrep --smart-case"
o.grepformat = "%f:%l:%c:%m"

o.splitright = true
o.splitbelow = true
o.splitkeep = "screen" -- keep text stable when splits open or close
o.smoothscroll = true
o.jumpoptions = "clean,view"
o.virtualedit = "block"

o.list = false
o.spelllang = "en,cjk" -- do not flag CJK characters

vim.opt.listchars = { tab = "» ", trail = "·", nbsp = "␣" }
vim.opt.nrformats:remove("octal")
vim.opt.wildoptions:append("fuzzy")
vim.opt.diffopt:append("algorithm:histogram")
vim.opt.formatoptions:append({ "m", "M" }) -- wrap at CJK characters, no space when joining CJK lines

if vim.env.SSH_TTY or vim.env.SSH_CONNECTION then vim.g.clipboard = "osc52" end
-- Sync with the system clipboard after startup.
vim.schedule(function() o.clipboard = "unnamedplus" end)

vim.g.python3_host_prog = vim.fn.expand("$CENTRAL_VENV_DIR/nvim/bin/python")
vim.g.loaded_node_provider = 0
vim.g.loaded_perl_provider = 0
vim.g.loaded_ruby_provider = 0

o.exrc = true -- load trusted project-local .nvim.lua
