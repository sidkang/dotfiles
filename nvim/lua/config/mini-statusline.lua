local M = {}

local branch_icon = "\u{e0a0}"
local diagnostic_symbols = { ERROR = "󰅚 ", WARN = "󰀪 ", INFO = "󰋽 ", HINT = "󰌶 " }

local function palette()
	local flavour = vim.o.background == "dark" and "mocha" or "latte"
	return require("catppuccin.palettes").get_palette(flavour)
end

local function set_highlights()
	local c = palette()
	local bar = vim.api.nvim_get_hl(0, { name = "StatusLine", link = false })
	local set = function(name, fg, extra)
		vim.api.nvim_set_hl(0, name, vim.tbl_extend("force", { fg = fg, bg = bar.bg }, extra or {}))
	end

	-- Mode blocks: a coloured space at both ends
	local blocks = { Normal = c.blue, Insert = c.green, Visual = c.sapphire, Replace = c.peach, Command = c.peach, Other = c.pink }
	for mode, color in pairs(blocks) do
		vim.api.nvim_set_hl(0, "MiniStatuslineMode" .. mode, { fg = color, bg = color })
	end

	set("MiniStatuslineDevinfo", c.subtext1)
	set("MiniStatuslineFilename", c.subtext0)
	set("MiniStatuslineFilenameModified", c.text, { bold = true })
	set("MiniStatuslineInactive", c.overlay1)
	set("MiniStatuslineLsp", c.lavender, { bold = true })
	set("MiniStatuslineFileinfo", c.pink)
	set("MiniStatuslineDiffAdd", c.green)
	set("MiniStatuslineDiffChange", c.peach)
	set("MiniStatuslineDiffDelete", c.red)
	set("MiniStatuslineDiagnosticError", c.red)
	set("MiniStatuslineDiagnosticWarn", c.yellow)
	set("MiniStatuslineDiagnosticInfo", c.sky)
	set("MiniStatuslineDiagnosticHint", c.teal)
end

local function branch()
	local label = require("utils.jj").label() or vim.b.minigit_summary_string
	return label and label ~= "" and (branch_icon .. " " .. label) or ""
end

local function diff()
	local s = vim.b.minidiff_summary
	if not s then return {} end
	return {
		{ hl = "MiniStatuslineDiffAdd", strings = { (s.add or 0) > 0 and ("+" .. s.add .. " ") or "" } },
		{ hl = "MiniStatuslineDiffChange", strings = { (s.change or 0) > 0 and ("~" .. s.change .. " ") or "" } },
		{ hl = "MiniStatuslineDiffDelete", strings = { (s.delete or 0) > 0 and ("-" .. s.delete .. " ") or "" } },
	}
end

local function diagnostics()
	local counts = vim.diagnostic.count(0)
	local groups = {}
	for _, name in ipairs({ "ERROR", "WARN", "INFO", "HINT" }) do
		local n = counts[vim.diagnostic.severity[name]]
		if n then
			local hl = "MiniStatuslineDiagnostic" .. name:sub(1, 1) .. name:sub(2):lower()
			table.insert(groups, { hl = hl, strings = { diagnostic_symbols[name] .. n .. " " } })
		end
	end
	return groups
end

local function filename()
	local name = vim.fn.expand("%:t")
	if name == "" then name = vim.bo.buftype == "" and "[No Name]" or "" end
	if vim.bo.modified then name = name .. "[+]" end
	if vim.bo.readonly or not vim.bo.modifiable then name = name .. "[-]" end
	return (name:gsub("%%", "%%%%"))
end

local function lsp()
	local names = vim.tbl_map(function(client) return client.name end, vim.lsp.get_clients({ bufnr = 0 }))
	if #names == 0 then return "" end
	return "[" .. table.concat(names, ",") .. "]" .. (vim.lsp.status() ~= "" and " …" or "")
end

local function compact(groups)
	return vim.tbl_filter(function(g) return type(g) == "string" or g.strings[1] ~= "" end, groups)
end

function M.setup()
	local statusline = require("mini.statusline")
	statusline.setup({
		use_icons = true,
		content = {
			active = function()
				local _, mode_hl = statusline.section_mode({ trunc_width = 0 })
				local file_hl = vim.bo.modified and "MiniStatuslineFilenameModified" or "MiniStatuslineFilename"
				local groups = {
					{ hl = mode_hl, strings = { " " } },
					" ",
					{ hl = "MiniStatuslineDevinfo", strings = { branch() } },
					" ",
				}
				vim.list_extend(groups, compact(diff()))
				vim.list_extend(groups, {
					"%<",
					{ hl = file_hl, strings = { filename() } },
					" ",
				})
				vim.list_extend(groups, diagnostics())
				vim.list_extend(groups, {
					"%=",
					{ hl = "MiniStatuslineLsp", strings = { lsp() } },
					" ",
					{ hl = "MiniStatuslineDevinfo", strings = { vim.bo.fileencoding ~= "" and vim.bo.fileencoding or vim.o.encoding } },
					" ",
					{ hl = "MiniStatuslineFileinfo", strings = { vim.bo.filetype:lower() } },
					" ",
					{ hl = mode_hl, strings = { " " } },
				})
				return statusline.combine_groups(groups)
			end,
			inactive = function()
				return statusline.combine_groups({
					{ hl = "MiniStatuslineInactive", strings = { filename() } },
					"%=",
					{ hl = "MiniStatuslineInactive", strings = { "%l:%c" } },
				})
			end,
		},
	})

	set_highlights()
	vim.api.nvim_create_autocmd("ColorScheme", {
		group = vim.api.nvim_create_augroup("user-statusline-hl", { clear = true }),
		callback = set_highlights,
	})
	vim.api.nvim_create_autocmd({ "DiagnosticChanged", "LspAttach", "LspDetach" }, {
		group = "user-statusline-hl",
		callback = function() vim.cmd.redrawstatus() end,
	})
end

return M
