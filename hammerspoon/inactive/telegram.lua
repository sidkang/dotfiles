local http = require("socket.http")
local ltn12 = require("ltn12")
local json = require("dkjson") -- You might need to install a JSON library, e.g., dkjson

-- Define the module table
local telegram = {}

-- Function to send a message to a Telegram chat
function telegram.sendMessage(bot_token, chat_id, text)
	-- Telegram API URL
	local url = "https://api.telegram.org/bot" .. bot_token .. "/sendMessage"

	-- Message payload
	local payload = {
		chat_id = chat_id,
		text = text,
	}

	-- Convert the payload to JSON
	local payload_json = json.encode(payload)

	-- Response handler
	local response_body = {}

	-- Make the HTTP POST request
	local res, code, response_headers = http.request({
		url = url,
		method = "POST",
		headers = {
			["Content-Type"] = "application/json",
			["Content-Length"] = tostring(#payload_json),
		},
		source = ltn12.source.string(payload_json),
		sink = ltn12.sink.table(response_body),
	})

	-- Check response
	if code ~= 200 then
		print("Error sending message: " .. (response_body[1] or "Unknown error"))
		return false
	end

	print("Message sent successfully")
	return true
end

-- Return the module table
return telegram
