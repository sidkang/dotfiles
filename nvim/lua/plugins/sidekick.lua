return {
	"folke/sidekick.nvim",
	opts = {
		-- add any options here
		cli = {
			mux = { backend = "tmux", enabled = true },
		},
	},
	keys = {
		{
			"<tab>",
			function()
				if not require("sidekick").nes_jump_or_apply() then
					return "<Tab>"
				end
			end,
			expr = true,
			desc = "Goto/Apply Next Edit Suggestion",
		},
		-- { "<c-.>", function() require("sidekick.cli").toggle() end, desc = "Sidekick Toggle", mode = { "n", "t", "i", "x" } },
		{
			"<leader>oo",
			function()
				require("sidekick.cli").toggle()
			end,
			desc = "Sidekick Toggle CLI",
		},
		{
			"<leader>os",
			function()
				require("sidekick.cli").select()
			end,
			-- Or to select only installed tools:
			-- require("sidekick.cli").select({ filter = { installed = true } })
			desc = "Select CLI",
		},
		{
			"<leader>ox",
			function()
				require("sidekick.cli").close()
			end,
			desc = "Detach a CLI Session",
		},
		{
			"<leader>ot",
			function()
				require("sidekick.cli").send({ msg = "{this}" })
			end,
			mode = { "x", "n" },
			desc = "Send This",
		},
		{
			"<leader>of",
			function()
				require("sidekick.cli").send({ msg = "{file}" })
			end,
			desc = "Send File",
		},
		{
			"<leader>ov",
			function()
				require("sidekick.cli").send({ msg = "{selection}" })
			end,
			mode = { "x" },
			desc = "Send Visual Selection",
		},
		{
			"<leader>op",
			function()
				require("sidekick.cli").prompt()
			end,
			mode = { "n", "x" },
			desc = "Sidekick Select Prompt",
		},
		-- Example of a keybinding to open Claude directly
		{
			"<leader>oc",
			function()
				require("sidekick.cli").toggle({ name = "opencode", focus = true })
			end,
			desc = "Sidekick Toggle opencode",
		},
	},
}
