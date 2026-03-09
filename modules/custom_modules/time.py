from pyrogram import Client, filters, enums
from pyrogram.types import Message
import aiohttp
from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+ required

from utils.misc import modules_help, prefix

GEO_API_USERNAME = "tahseen"
WEATHER_API_KEY = "3ec738bcb912c44a805858054ead1efd"
DEFAULT_CITY = "Los Angeles"

WEATHER_EMOJIS = {
    "clear sky": "☀️",
    "few clouds": "🌤️",
    "scattered clouds": "⛅️",
    "broken clouds": "☁️",
    "overcast clouds": "🌥️",
    "light rain": "🌧️",
    "moderate rain": "🌧️",
    "heavy rain": "🌧️",
    "shower snow": "🌨️",
    "light snow": "🌨️",
    "thunderstorm": "⛈️",
    "snow": "🌨️",
    "mist": "🌫️",
    "haze": "🌫️",
    "smoke": "💨",
}

async def fetch_json(url: str, params: dict) -> dict:
    """Fetch JSON data from a URL with provided parameters."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            return {"error": str(e)}

async def get_coordinates(city_name: str):
    """Get the coordinates (latitude, longitude) for a given city name."""
    search_url = "http://api.geonames.org/searchJSON"
    params = {'q': city_name, 'username': GEO_API_USERNAME, 'maxRows': 1}
    data = await fetch_json(search_url, params)
    if 'geonames' in data and data['geonames']:
        return data['geonames'][0]['lat'], data['geonames'][0]['lng']
    return None, None

async def fetch_weather_data(city_name: str):
    """Fetches weather data from the OpenWeatherMap API."""
    weather_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {'q': city_name, 'appid': WEATHER_API_KEY, 'units': 'metric'}
    return await fetch_json(weather_url, params)

async def get_city_time(city_name: str = DEFAULT_CITY) -> str:
    """Get the current time and a brief weather summary for a city."""
    lat, lng = await get_coordinates(city_name)
    if not lat or not lng:
        return "<b>Error:</b> <i>City not found or invalid city name.</i>"

    time_url = "http://api.geonames.org/timezoneJSON"
    params = {'username': GEO_API_USERNAME, 'lat': lat, 'lng': lng}
    data = await fetch_json(time_url, params)
    
    if 'timezoneId' in data:
        timezone = ZoneInfo(data['timezoneId'])
        city_time = datetime.now(timezone)
        time_24hr = city_time.strftime('%H:%M:%S')
        time_12hr = city_time.strftime('%I:%M %p')
        date = city_time.strftime('%Y-%m-%d %A')
        
        weather_data = await fetch_weather_data(city_name)
        if 'weather' in weather_data and 'main' in weather_data:
            temp = weather_data['main']['temp']
            description = weather_data['weather'][0]['description']
            emoji = WEATHER_EMOJIS.get(description.lower(), "")
            weather_summary = f"<b>WX:</b> {description.capitalize()} {temp}°C {emoji}".strip()
        else:
            weather_summary = "<b>WX:</b> N/A"

        return (
            f"<blockquote><b>Currently in {city_name.title()}:</b></blockquote>\n"
            f"<blockquote>"
            f"<b>Time:</b> {time_24hr} / {time_12hr}\n"
            f"<b>Date:</b> {date}\n"
            f"<b>TZ:</b> {data['timezoneId']}\n"
            f"{weather_summary}"
            f"</blockquote>"
        )
    return "<b>Error:</b> <i>Unable to get time for the specified coordinates.</i>"

async def get_weather(city_name: str = DEFAULT_CITY) -> str:
    """Get the full weather details for a city."""
    data = await fetch_weather_data(city_name)
    
    if 'weather' in data and 'main' in data:
        temp = data['main']['temp']
        feels_like = data['main']['feels_like']
        humidity = data['main']['humidity']
        description = data['weather'][0]['description']
        wind_speed = data['wind']['speed']
        emoji = WEATHER_EMOJIS.get(description.lower(), "")
        return (
            f"<blockquote><b>Weather in {city_name.title()}:</b></blockquote>\n"
            f"<blockquote>"
            f"<b>Condition:</b> {description.capitalize()} {emoji}\n"
            f"<b>Temperature:</b> {temp}°C\n"
            f"<b>Feels Like:</b> {feels_like}°C\n"
            f"<b>Humidity:</b> {humidity}%\n"
            f"<b>Wind Speed:</b> {wind_speed} m/s"
            f"</blockquote>"
        )
    return "<b>Error:</b> <i>Unable to get weather for the specified city.</i>"

@Client.on_message(filters.command("time", prefix))
async def time_command(client: Client, message: Message):
    """Handle the time command to show the current time and weather for a city."""
    city_name = message.reply_to_message.text.strip() if message.reply_to_message else None
    if not city_name:
        args = message.text.split(maxsplit=1)
        city_name = args[1].strip() if len(args) > 1 else DEFAULT_CITY

    result = await get_city_time(city_name)
    
    if message.from_user.is_self:
        await message.edit(result, parse_mode=enums.ParseMode.HTML)
    else:
        await message.reply(result, parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command("weather", prefix))
async def weather_command(client: Client, message: Message):
    """Handle the weather command to show the current weather for a city."""
    city_name = message.reply_to_message.text.strip() if message.reply_to_message else None
    if not city_name:
        args = message.text.split(maxsplit=1)
        city_name = args[1].strip() if len(args) > 1 else DEFAULT_CITY

    result = await get_weather(city_name)
    
    if message.from_user.is_self:
        await message.edit(result, parse_mode=enums.ParseMode.HTML)
    else:
        await message.reply(result, parse_mode=enums.ParseMode.HTML)

modules_help["time"] = {
    "time [city]": "Shows the current time and weather.",
    "weather [city]": "Shows the current weather details."
}
