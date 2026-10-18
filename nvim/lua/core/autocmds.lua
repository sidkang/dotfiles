vim.filetype.add({
	extension = {
		bean = "beancount",
		list = "list",
	},
	filename = {
		["Caddyfile"] = "caddyfile",
	},
})

vim.api.nvim_create_autocmd("FileType", {
	pattern = { "json", "list" },
	callback = function(args)
		local ft = vim.bo[args.buf].filetype
		local cs = {
			json = "// %s",
			list = "// %s",
		}
		if cs[ft] then
			vim.bo[args.buf].commentstring = cs[ft]
		end
	end,
})

vim.api.nvim_create_autocmd({ "InsertLeave", "CmdlineEnter" }, {
	desc = "After event activate en input method",
	group = vim.api.nvim_create_augroup("auto_input_method_activate", { clear = true }),
	pattern = { "*" },
	callback = function()
		vim.system({ "open", "-g", "hammerspoon://switchIME?to=en" })
	end,
})

-- auto toggle cmdline when needed
-- vim.cmd [[au CmdlineEnter * silent! lua vim.o.cmdheight = 1]]
-- vim.cmd [[au CmdlineLeave * silent! lua vim.o.cmdheight = 0]]
-- local cmd_group = vim.api.nvim_create_augroup("DynamicCmdHeight", { clear = true })
--
-- vim.api.nvim_create_autocmd("CmdlineEnter", {
-- 	group = cmd_group,
-- 	callback = function() vim.opt.cmdheight = 1 end,
-- })
--
-- vim.api.nvim_create_autocmd("CmdlineLeave", {
-- 	group = cmd_group,
-- 	callback = function() vim.opt.cmdheight = 0 end,
-- })

vim.api.nvim_create_autocmd("TextYankPost", {
	callback = function()
		vim.hl.on_yank()
	end,
})
