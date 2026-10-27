return {
	-- Provides the default server configs; overrides live in lsp/*.lua
	"neovim/nvim-lspconfig",
	config = function()
		local group = vim.api.nvim_create_augroup("user-lsp", { clear = true })

		vim.api.nvim_create_autocmd("LspAttach", {
			group = group,
			callback = function(event)
				local client = vim.lsp.get_client_by_id(event.data.client_id)
				if not client then return end
				local buf = event.buf
				local map = function(keys, func, desc)
					vim.keymap.set("n", keys, func, { buffer = buf, desc = "LSP: " .. desc })
				end

				-- Defaults: grn rename, gra code action, grr references, gri implementation, grt type definition, gO symbols
				map("gd", vim.lsp.buf.definition, "[G]oto [D]efinition")
				map("gD", vim.lsp.buf.declaration, "[G]oto [D]eclaration")

				if client:supports_method("textDocument/documentHighlight", buf) then
					local highlight = vim.api.nvim_create_augroup("user-lsp-highlight-" .. buf, { clear = true })
					vim.api.nvim_create_autocmd({ "CursorHold", "CursorHoldI" }, { group = highlight, buffer = buf, callback = vim.lsp.buf.document_highlight })
					vim.api.nvim_create_autocmd({ "CursorMoved", "CursorMovedI" }, { group = highlight, buffer = buf, callback = vim.lsp.buf.clear_references })
				end

				if client:supports_method("textDocument/inlayHint", buf) then
					map("<leader>uh", function()
						vim.lsp.inlay_hint.enable(not vim.lsp.inlay_hint.is_enabled({ bufnr = buf }), { bufnr = buf })
					end, "[U]I Toggle Inlay [H]ints")
				end
			end,
		})

		vim.api.nvim_create_autocmd("LspDetach", {
			group = group,
			callback = function(event)
				vim.lsp.buf.clear_references()
				pcall(vim.api.nvim_del_augroup_by_name, "user-lsp-highlight-" .. event.buf)
			end,
		})

		vim.api.nvim_create_autocmd("LspProgress", {
			group = group,
			callback = function() vim.cmd.redrawstatus() end,
		})

		vim.lsp.enable({ "lua_ls", "basedpyright", "ruff", "beancount", "fish_lsp", "bashls", "yamlls", "jsonls", "taplo" })
	end,
}
