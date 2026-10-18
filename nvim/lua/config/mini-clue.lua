local miniclue = require("mini.clue")

local M = {}

function M.setup()
	miniclue.setup({
		triggers = {
			{ mode = "n", keys = "<leader>" },
			{ mode = "x", keys = "<leader>" },
			{ mode = "n", keys = "<localleader>" },
			{ mode = "x", keys = "<localleader>" },
			{ mode = "i", keys = "<C-x>" },
			{ mode = "n", keys = "g" },
			{ mode = "x", keys = "g" },
			{ mode = "n", keys = "'" },
			{ mode = "n", keys = "`" },
			{ mode = "x", keys = "'" },
			{ mode = "x", keys = "`" },
			{ mode = "n", keys = '"' },
			{ mode = "x", keys = '"' },
			{ mode = "i", keys = "<C-r>" },
			{ mode = "c", keys = "<C-r>" },
			{ mode = "n", keys = "<C-w>" },
			{ mode = "n", keys = "z" },
			{ mode = "x", keys = "z" },
			{ mode = "n", keys = "[" },
			{ mode = "n", keys = "]" },
		},
		clues = {
			{ mode = "n", keys = "<leader>c", desc = "+Code" },
			{ mode = "n", keys = "<leader>s", desc = "+Search" },
			{ mode = "n", keys = "<leader>u", desc = "+Toggle" },
			{ mode = "n", keys = "<leader>w", desc = "+Window" },
			miniclue.gen_clues.builtin_completion(),
			miniclue.gen_clues.g(),
			miniclue.gen_clues.marks(),
			miniclue.gen_clues.registers(),
			miniclue.gen_clues.windows(),
			miniclue.gen_clues.z(),
		},
		window = {
			config = {
				width = "auto",
			},
			delay = 500,
		},
	})
end

return M
