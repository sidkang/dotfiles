---@class MiniGitModule
---@field keys LazyKeysSpec[]
---@field setup fun()

local M = {}

---@type LazyKeysSpec[]
M.keys = {
	{ "<leader>gs", function() MiniGit.show_at_cursor() end, mode = { "n", "x" }, desc = "Show at Cursor" },
	{ "<leader>gh", function() MiniGit.show_range_history() end, mode = { "n", "x" }, desc = "Range History" },
	{ "<leader>gb", "<cmd>Git blame -- %<CR>", desc = "Blame File" },
	{ "<leader>gd", "<cmd>Git diff -- %<CR>", desc = "Diff File" },
}

function M.setup()
	require("mini.git").setup()
end

---@return MiniGitModule
return M
