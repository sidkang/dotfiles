vim.opt_local.shiftwidth = 4
vim.bo.commentstring = "; %s"

local map = function(mode, lhs, rhs, desc)
	vim.keymap.set(mode, lhs, rhs, { buffer = 0, desc = desc })
end

map("n", "+", "<C-a>", "Increment number")
map("n", "-", "<C-x>", "Decrement number")
map("x", "+", "<C-a>", "Increment number")
map("x", "-", "<C-x>", "Decrement number")
