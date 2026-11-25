local in_flight = nil

-- Work around upstream bugs in saghen/blink.lib (managed:download never resolves
-- task.new(), and native.download passes tostring(nil) as an error), and avoid
-- requiring blink.pairs during lazy.nvim's build step before the binary exists.
local function download_library(plugin, on_done)
	local native = require("blink.lib.native")
	local repo_root = plugin.dir
	vim.opt.runtimepath:append(repo_root)

	local commit = native.try_git_commit(repo_root)
	if commit and native.resolve("blink_pairs_parser", commit) then
		if on_done then on_done(true) end
		return true
	end

	local tag = native.git_tag(repo_root)
	local platform = native.platform()
	if not commit or not tag or not platform.triple then
		local err = "blink.pairs: cannot resolve release metadata for native library"
		if on_done then on_done(false, err) end
		return false, err
	end

	if not in_flight then
		local lib_path = native.library_path(repo_root, "blink_pairs_parser", commit)
		local tmp_path = ("%s.%d.tmp"):format(lib_path, vim.uv.hrtime())
		local url = ("https://github.com/saghen/blink.pairs/releases/download/%s/%s%s"):format(
			tag,
			platform.triple,
			platform.lib_extension
		)
		native.mkdirp(vim.fs.dirname(lib_path))

		local state = { done = false, ok = false, err = nil, callbacks = {} }
		in_flight = state
		state.req = vim.net.request(url, { outpath = tmp_path }, function(err)
			if err then
				vim.uv.fs_unlink(tmp_path)
				state.err = err
			else
				local renamed, rename_err = vim.uv.fs_rename(tmp_path, lib_path)
				if not renamed then
					vim.uv.fs_unlink(tmp_path)
					state.err = rename_err
				end
			end
			vim.schedule(function()
				state.ok = state.err == nil and native.resolve("blink_pairs_parser", commit) ~= nil
				if not state.ok and not state.err then state.err = "failed to resolve downloaded library" end
				state.done = true
				in_flight = nil
				for _, cb in ipairs(state.callbacks) do
					cb(state.ok, state.err)
				end
			end)
		end)
	end

	local state = in_flight
	if on_done then
		table.insert(state.callbacks, on_done)
		return
	end

	if not vim.wait(30000, function() return state.done end) then
		if #state.callbacks == 0 then
			state.req:close()
			in_flight = nil
		end
		return false, "timed out downloading blink.pairs native library"
	end
	return state.ok, state.err
end

return {
	"saghen/blink.pairs",
	version = "*", -- (recommended) only required with prebuilt binaries
	dependencies = "saghen/blink.lib",
	build = function(plugin)
		assert(download_library(plugin))
	end,
	config = function(plugin, opts)
		local blink_pairs = require("blink.pairs")
		if blink_pairs.library_available() then
			blink_pairs.setup(opts)
			return
		end
		download_library(plugin, function(ok, err)
			if ok then
				blink_pairs.setup(opts)
			else
				vim.notify("blink.pairs: " .. (err or "failed to download native library"), vim.log.levels.WARN)
			end
		end)
	end,

	--- @module 'blink.pairs'
	--- @type blink.pairs.Config
	opts = {
		mappings = {
			enabled = true,
			cmdline = true,
			disabled_filetypes = {},
			pairs = {},
		},
		highlights = {
			enabled = true,
			cmdline = true,
			groups = {
				"BlinkPairsOrange",
				"BlinkPairsPurple",
				"BlinkPairsBlue",
			},
			unmatched_group = "BlinkPairsUnmatched",

			matchparen = {
				enabled = true,
				cmdline = false,
				include_surrounding = false,
				group = "BlinkPairsMatchParen",
				priority = 250,
			},
		},
		debug = false,
	},
}
