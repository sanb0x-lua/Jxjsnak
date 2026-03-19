local server = "https://jxjsnak.onrender.com"

-- Простейший HWID (можно улучшить)
local hwid = gg.getTargetPackage() .. "_" .. gg.getLocale()

local input = gg.prompt({"Введите ключ:"}, {""}, {"text"})
if not input then os.exit() end

local key = input[1]:gsub("%s+", "")

local url = server .. "/check_key?key=" .. key .. "&hwid=" .. hwid
local response = gg.makeRequest(url)

if response and response.content then
    print(response.content)

    if response.content:find('"expired":true') then
        gg.alert("⛔ Ваш ключ закончился!")
        os.exit()
    end

    if response.content:find('"ok":true') then
        gg.alert("🎉 Доступ разрешён!")
    else
        gg.alert("❌ Неверный ключ или другой HWID!")
        os.exit()
    end
else
    gg.alert("Ошибка соединения!")
    os.exit()
end