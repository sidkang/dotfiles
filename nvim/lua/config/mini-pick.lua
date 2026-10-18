---@class MiniPickModule
---@field keys LazyKeysSpec[]
---@field setup fun()

local M = {}

local lsp_picker = function(scope)
	return function()
		MiniExtra.pickers.lsp({ scope = scope })
	end
end

---@type LazyKeysSpec[]
M.keys = {
	{
		"<leader>sf",
		function()
			MiniPick.builtin.files()
		end,
		desc = "Find Files",
	},
	{
		"<leader>sg",
		function()
			MiniPick.builtin.grep_live()
		end,
		desc = "Grep",
	},
	{
		"<leader>sb",
		function()
			MiniPick.builtin.buffers()
		end,
		desc = "Buffers",
	},
	{
		"<leader>sk",
		function()
			MiniExtra.pickers.keymaps()
		end,
		desc = "Keymaps",
	},
	{
		"<leader>sd",
		function()
			MiniExtra.pickers.diagnostic()
		end,
		desc = "Diagnostics",
	},
	{
		"<leader>sx",
		function()
			MiniExtra.pickers.diagnostic({
				get_opts = { severity = vim.diagnostic.severity.ERROR },
			})
		end,
		desc = "Diagnostic Errors",
	},
	{
		"<leader>sD",
		function()
			MiniExtra.pickers.diagnostic({ scope = "current" })
		end,
		desc = "Buffer Diagnostics",
	},
	{
		"<leader>sc",
		function()
			MiniExtra.pickers.history({ scope = ":" })
		end,
		desc = "Command History",
	},
	{
		'<leader>s"',
		function()
			MiniExtra.pickers.registers()
		end,
		desc = "Registers",
	},
	{
		"<leader>sl",
		function()
			MiniExtra.pickers.buf_lines({ scope = "current" })
		end,
		desc = "Buffer Lines",
	},
	{
		"<leader>sw",
		function()
			MiniPick.builtin.grep({ pattern = vim.fn.expand("<cword>") })
		end,
		desc = "Word",
	},
	{
		"<leader>sh",
		function()
			MiniPick.builtin.help()
		end,
		desc = "Help Pages",
	},
	{
		"<leader>sH",
		function()
			MiniExtra.pickers.hl_groups()
		end,
		desc = "Highlights",
	},
	{
		"<leader>sq",
		function()
			MiniExtra.pickers.list({ scope = "quickfix" })
		end,
		desc = "Quickfix List",
	},
	{ "<leader>si", lsp_picker("implementation"), desc = "LSP Implementation" },
	{ "<leader>sr", lsp_picker("references"), desc = "LSP References" },
	{ "<leader>ss", lsp_picker("document_symbol"), desc = "Document Symbols" },
	{ "<leader>sS", lsp_picker("workspace_symbol_live"), desc = "Workspace Symbols" },
	{ "<leader>st", lsp_picker("type_definition"), desc = "LSP Type Definition" },
	{
		"<leader>sm",
		function()
			MiniExtra.pickers.marks()
		end,
		desc = "Marks",
	},
}

function M.setup()
	require("mini.pick").setup({
		window = {
			config = function()
				local height = math.floor(vim.o.lines * 0.6)
				local width = math.floor(vim.o.columns * 0.7)

				return {
					anchor = "NW",
					border = "rounded",
					height = height,
					row = math.floor((vim.o.lines - height) / 2),
					col = math.floor((vim.o.columns - width) / 2),
					width = width,
				}
			end,
		},
	})
	require("mini.extra").setup()
	vim.ui.select = MiniPick.ui_select
end

return M
