---@type LazySpec
return {
	"stevearc/conform.nvim",
	event = { "BufWritePre" },
	cmd = { "ConformInfo" },
	keys = {
		{
			"<leader>cf",
			function()
				require("conform").format({ async = true, lsp_format = "fallback" })
			end,
			mode = { "n", "x" },
			desc = "Format Buffer",
		},
	},
	opts = {
		default_format_opts = {
			lsp_format = "fallback",
		},
		notify_on_error = false,
		notify_no_formatters = false,
		format_on_save = function(bufnr)
			local disable_filetypes = { c = true, cpp = true }
			return {
				timeout_ms = 2000,
				lsp_format = disable_filetypes[vim.bo[bufnr].filetype] and "never" or "fallback",
			}
		end,
		formatters_by_ft = {
			bash = { "shfmt" },
			beancount = { "bean-format" },
			caddyfile = { "caddy" },
			clojure = { "cljfmt", "joker", stop_after_first = true },
			fish = { "fish_indent" },
			javascript = { "prettier" },
			json = { "prettier" },
			lua = { "stylua" },
			markdown = { "prettier" },
			python = { "ruff_organize_imports", "ruff_fix", "ruff_format" },
			toml = { "taplo" },
			yaml = { "yamlfmt" },
		},
		formatters = {
			["bean-format"] = {
				-- Mason only links `bh`; bean-format lives in the beanhub-cli venv
				command = vim.fn.stdpath("data") .. "/mason/packages/beanhub-cli/venv/bin/bean-format",
				prepend_args = { "-c", "70" },
			},
			caddy = {
				command = "caddy",
				args = { "fmt", "-" },
			},
			ruff_format = {
				append_args = { "--line-length", "130" },
			},
			stylua = {
				prepend_args = {
					"--indent-width",
					"2",
					"--column-width",
					"220",
					"--call-parentheses",
					"Input",
					"--collapse-simple-statement",
					"Always",
				},
			},
			taplo = {
				inherit = false,
				command = "taplo",
				args = { "format", "--option", "column_width=140", "--option", "allowed_blank_lines=1", "-" },
			},
			yamlfmt = {
				prepend_args = {
					"-formatter",
					"indent=2",
					"include_document_start=true",
					"indentless_arrays=false",
					"trim_trailing_whitespace=true",
					"scan_folded_as_literal=true",
				},
			},
		},
	},
}
