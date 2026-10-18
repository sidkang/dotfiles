---@class MiniFilesModule
---@field keys LazyKeysSpec[]
---@field setup fun()

local M = {}

local filter_entries = {
	".jj",
	".git",
	".DS_Store",
	".ruff_cache",
	"__pycache__",
	"node_modules",
}

---@type LazyKeysSpec[]
M.keys = {
	{
		"<leader>se",
		function()
			MiniFiles.open(vim.api.nvim_buf_get_name(0))
		end,
		mode = { "n", "x" },
		desc = "Mini File Explorer",
	},
}

function M.setup()
	-- Neovim 0.12 can error here if the legacy FileExplorer augroup was never created.
	vim.api.nvim_create_augroup("FileExplorer", { clear = true })

	require("mini.files").setup({
		options = {
			use_as_default_explorer = true,
		},
		content = {
			filter = function(fs_entry)
				for _, entry in ipairs(filter_entries) do
					if fs_entry.name == entry then
						return false
					end
				end
				return true
			end,
		},
		mappings = {
			go_in = "L",
			go_in_plus = "l",
			go_out = "H",
			go_out_plus = "h",
		},
		windows = {
			preview = true,
			width_focus = 35,
			width_preview = 60,
		},
	})
end

return M
