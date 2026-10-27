---@class MiniDiffModule
---@field keys LazyKeysSpec[]
---@field setup fun()

local M = {}

---@type LazyKeysSpec[]
M.keys = {
	{ "<leader>uo", function() MiniDiff.toggle_overlay() end, desc = "Toggle Diff Overlay" },
	{ "<leader>gq", function() MiniDiff.export("qf") end, desc = "Hunks to Quickfix" },
}

--- Diff against the parent of the working-copy commit (`@-`) in jj repos; other buffers fall through to git.
local function jj_source()
	local jj = require("utils.jj")
	local attached = {} ---@type table<integer, boolean>

	---@return string? root, string? fileset
	local function locate(buf)
		local root, path = jj.root(buf), vim.api.nvim_buf_get_name(buf)
		local rel = root and path ~= "" and vim.fs.relpath(root, path)
		if rel then return root, ('root-file:"%s"'):format((rel:gsub('["\\]', "\\%0"))) end
	end

	local function update(buf)
		local root, fileset = locate(buf)
		if not root then return end
		jj.run(root, { "file", "show", "-r", "@-", fileset }, function(result)
			if not attached[buf] or not vim.api.nvim_buf_is_valid(buf) then return end
			if result.code == 0 then
				MiniDiff.set_ref_text(buf, result.stdout)
			elseif result.stderr:find("No such path", 1, true) then
				MiniDiff.set_ref_text(buf, "") -- new file: every line is an addition
			else
				attached[buf] = nil
				MiniDiff.fail_attach(buf)
			end
		end)
	end

	vim.api.nvim_create_autocmd({ "FocusGained", "ShellCmdPost", "TermLeave", "TermClose" }, {
		group = vim.api.nvim_create_augroup("user-jj-diff", { clear = true }),
		callback = function()
			for buf in pairs(attached) do
				update(buf)
			end
		end,
	})

	return {
		name = "jj",
		attach = function(buf)
			if not locate(buf) then return false end
			attached[buf] = true
			update(buf)
		end,
		detach = function(buf) attached[buf] = nil end,
	}
end

function M.setup()
	local mini_diff = require("mini.diff")
	mini_diff.setup({
		source = { jj_source(), mini_diff.gen_source.git() },
	})
end

---@return MiniDiffModule
return M
