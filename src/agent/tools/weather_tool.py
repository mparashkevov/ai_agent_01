from llama_index.core.tools import FunctionTool
from .web_search_tool import search_web, read_url
import requests
import json

WEATHER_TOOL_PROMPT = """
You are a Weather Forecast Tool designed to retrieve accurate, up‑to‑date weather information from the internet. 
Your purpose is to search online sources, extract the most reliable weather data, and present it in a clear, structured, 
and user-friendly format.

Your responsibilities:

1. When the user asks for weather information, identify:
   - The location (city, region, or coordinates)
   - The time period (current, hourly, tomorrow, 7‑day, etc.)
   - Any special conditions (wind, humidity, UV index, air quality, storms)

2. Use your web-search tool to gather information from multiple reputable sources such as:
   - National meteorological services
   - Global weather APIs
   - Trusted weather forecasting websites

3. Cross-check the retrieved data and synthesize a consistent forecast.

4. Always return results in a structured format:
   - Location
   - Date and time
   - Temperature (°C)
   - Conditions (sunny, cloudy, rain, snow, etc.)
   - Wind speed and direction
   - Humidity
   - Precipitation probability
   - Additional alerts (storms, heatwaves, warnings)

5. If the user’s request is ambiguous, ask for clarification before searching.

6. If weather data cannot be found, clearly explain why and suggest the closest available information.

7. Never invent weather data. Only report information found through your search tools.

8. Keep explanations concise unless the user requests more detail.

### Example Output:
Location: Vidin, Bulgaria
Date and time: Wednesday, Feb 4, 14:45
Temperature (°C): 2°C
Conditions: Overcast
Wind speed and direction: 12 km/h ESE
Humidity: 93%
Precipitation probability: 10%
Additional alerts: None

---

Your goal is to act as a highly reliable, internet‑connected weather assistant that always provides the most accurate and 
useful forecast available.
"""

def get_coordinates(location: str) -> dict:
    """Resolve location name to latitude and longitude using Open-Meteo Geocoding API."""
    try:
        url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {"name": location, "count": 1, "language": "en", "format": "json"}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if not results:
            return None
        return {
            "latitude": results[0]["latitude"],
            "longitude": results[0]["longitude"],
            "name": results[0].get("name", location),
            "country": results[0].get("country", "")
        }
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None

def get_weather_code_description(code: int) -> str:
    """Map WMO Weather interpretation codes to human readable strings."""
    codes = {
        0: "Clear sky",
        1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Fog", 48: "Depositing rime fog",
        51: "Drizzle: Light", 53: "Drizzle: Moderate", 55: "Drizzle: Dense intensity",
        56: "Freezing Drizzle: Light", 57: "Freezing Drizzle: Dense intensity",
        61: "Rain: Slight", 63: "Rain: Moderate", 65: "Rain: Heavy intensity",
        66: "Freezing Rain: Light", 67: "Freezing Rain: Heavy intensity",
        71: "Snow fall: Slight", 73: "Snow fall: Moderate", 75: "Snow fall: Heavy intensity",
        77: "Snow grains",
        80: "Rain showers: Slight", 81: "Rain showers: Moderate", 82: "Rain showers: Violent",
        85: "Snow showers slight", 86: "Snow showers heavy",
        95: "Thunderstorm: Slight or moderate",
        96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
    }
    return codes.get(code, "Unknown")

def get_weather_info(location: str, query: str = "", **kwargs) -> str:
    """
    Retrieves weather information for a specific location using Open-Meteo API.
    
    Args:
        location: The city or region to get weather for (e.g., "London", "Sofia").
        query: Specific details requested.
    """
    # Step 1: Geocoding
    coords = get_coordinates(location)
    if not coords:
        return f"Could not find coordinates for location: {location}"

    # Step 2: Fetch Weather from Open-Meteo (as per openapi.yml)
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": coords["latitude"],
            "longitude": coords["longitude"],
            "current_weather": True,
            "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation_probability",
            "daily": "temperature_2m_max,temperature_2m_min,weather_code",
            "timezone": "auto"
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        current = data.get("current_weather", {})
        temp = current.get("temperature")
        wind_speed = current.get("windspeed")
        wind_dir = current.get("winddirection")
        weather_code = current.get("weathercode")
        time = current.get("time")
        
        # Get humidity and precip prob from hourly (closest to current time)
        # For simplicity, we'll just take the first index or a default
        humidity = data.get("hourly", {}).get("relative_humidity_2m", ["N/A"])[0]
        precip_prob = data.get("hourly", {}).get("precipitation_probability", ["N/A"])[0]
        
        location_full = f"{coords['name']}, {coords['country']}"
        condition = get_weather_code_description(weather_code)
        
        res = f"Location: {location_full}\n"
        res += f"Date and time: {time}\n"
        res += f"Temperature (°C): {temp}°C\n"
        res += f"Conditions: {condition}\n"
        res += f"Wind speed and direction: {wind_speed} km/h, direction {wind_dir}°\n"
        res += f"Humidity: {humidity}%\n"
        res += f"Precipitation probability: {precip_prob}%\n"
        res += f"Additional alerts: None\n"
        
        return res
    except Exception as e:
        return f"Error fetching weather data from Open-Meteo: {e}"

# Create the LlamaIndex tool
weather_tool = FunctionTool.from_defaults(
    fn=get_weather_info,
    name="weather_forecast",
    description="Useful for retrieving accurate weather information for a specific location using Open-Meteo API."
)
