return {
	filetypes = { "lua" },
	on_init = function(client)
		if client.workspace_folders then
			local path = client.workspace_folders[1].name
			if
				path ~= vim.fn.stdpath("config")
				and (vim.uv.fs_stat(path .. "/.luarc.json") or vim.uv.fs_stat(path .. "/.luarc.jsonc"))
			then
				return
			end
		end
		client.config.settings.Lua = vim.tbl_deep_extend("force", client.config.settings.Lua, {
			runtime = {
				version = "LuaJIT",
				path = { "lua/?.lua", "lua/?/init.lua" },
			},
			workspace = {
				checkThirdParty = false,
				library = vim.tbl_extend("force", vim.api.nvim_get_runtime_file("", true), {
					"${3rd}/luv/library",
					"${3rd}/busted/library",
				}),
			},
		})
	end,
	settings = {
		Lua = {
			completion = {
				callSnippet = "Replace",
			},
			diagnostics = { globals = { "vim", "hs" } },
			hint = { enable = true, arrayIndex = "Disable" },
			runtime = {
				version = "LuaJIT",
			},
			telemetry = { enable = false },
			workspace = {
				library = {
					[vim.fn.expand("$VIMRUNTIME/lua")] = true,
					[vim.fn.expand("$VIMRUNTIME/lua/vim/lsp")] = true,
					[vim.fn.expand("$HOME/.config/hammerspoon/Spoons/EmmyLua.spoon/annotations")] = true,
				},
			},
		},
	},
}
