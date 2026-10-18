---@class MiniDiffModule
---@field keys LazyKeysSpec[]
---@field setup fun()

local M = {}

---@type LazyKeysSpec[]
M.keys = {
	{
		"<leader>uo",
		function()
			MiniDiff.toggle_overlay()
		end,
		desc = "Toggle Diff Overlay",
	},
}

function M.setup()
	require("mini.diff").setup({})
end

---@return MiniDiffModule
return M
