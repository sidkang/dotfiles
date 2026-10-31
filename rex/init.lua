-- Rex server configuration. Keep client operations inside actions.
-- Font and window appearance remain in the macOS app's Settings.
-- https://www.superlogical.com/rex/docs/customize/config

rex.action {
  name = "use_latte",
  title = "Use Catppuccin Latte",
  description = "Select the already-imported catppuccin-latte theme.",
  category = "Appearance",
  keywords = "theme light catppuccin latte",
  run = function(ctx, args)
    rex.client.queue("client.theme.change", { name = "catppuccin-latte" })
  end,
}

-- No custom keybindings yet: Kitty migration groups C-F are not approved.
