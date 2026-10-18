local M = {}

local function clamp(value, min, max)
	return math.min(max, math.max(min, value))
end

local function hex_to_rgb(hex)
	hex = hex:gsub("#", "")
	return tonumber(hex:sub(1, 2), 16) / 255, tonumber(hex:sub(3, 4), 16) / 255, tonumber(hex:sub(5, 6), 16) / 255
end

local function rgb_to_hex(r, g, b)
	return string.format(
		"#%02x%02x%02x",
		math.floor(clamp(r, 0, 1) * 255 + 0.5),
		math.floor(clamp(g, 0, 1) * 255 + 0.5),
		math.floor(clamp(b, 0, 1) * 255 + 0.5)
	)
end

local function rgb_to_hsl(r, g, b)
	local max = math.max(r, g, b)
	local min = math.min(r, g, b)
	local h, s
	local l = (max + min) / 2

	if max == min then
		h, s = 0, 0
	else
		local d = max - min
		s = l > 0.5 and d / (2 - max - min) or d / (max + min)

		if max == r then
			h = ((g - b) / d + (g < b and 6 or 0)) / 6
		elseif max == g then
			h = ((b - r) / d + 2) / 6
		else
			h = ((r - g) / d + 4) / 6
		end
	end

	return h, s, l
end

local function hsl_to_rgb(h, s, l)
	local function hue_to_rgb(p, q, t)
		if t < 0 then
			t = t + 1
		end
		if t > 1 then
			t = t - 1
		end
		if t < 1 / 6 then
			return p + (q - p) * 6 * t
		end
		if t < 1 / 2 then
			return q
		end
		if t < 2 / 3 then
			return p + (q - p) * (2 / 3 - t) * 6
		end
		return p
	end

	if s == 0 then
		return l, l, l
	end

	local q = l < 0.5 and l * (1 + s) or l + s - l * s
	local p = 2 * l - q

	return hue_to_rgb(p, q, h + 1 / 3), hue_to_rgb(p, q, h), hue_to_rgb(p, q, h - 1 / 3)
end

function M.saturate(hex, amount)
	return M.adjust(hex, amount, 0)
end

function M.lighten(hex, amount)
	return M.adjust(hex, 0, amount)
end

function M.adjust(hex, saturation, lightness)
	local h, s, l = rgb_to_hsl(hex_to_rgb(hex))
	s = clamp(s + (saturation or 0), 0, 1)
	l = clamp(l + (lightness or 0), 0, 1)
	return rgb_to_hex(hsl_to_rgb(h, s, l))
end

return M
