"""Optional OAWeather presentation using its native source and converter."""

import math


def weather_ready(source, enabled):
    if source is None or not enabled:
        return False
    try:
        value = source.getCurrentVal("temp", None)
        return not isinstance(value, bool) and math.isfinite(float(value))
    except (AttributeError, TypeError, ValueError):
        return False


def weather_label(parent, x, y, w, h, mode, font=20, **attrs):
    from .layout import convert, label
    return convert(label(parent, x, y, w, h, source="session.OAWeather", font=font,
                         zPosition="1", **attrs), "OAWeather", mode)


def weather_icon(parent, x, y, size, day="current"):
    widget = weather_label(parent, x, y, size, size, "meteocode," + day,
                           halign="center", noWrap="1")
    widget.set("font", f"UmbraWeatherIcons;{round(size * .76)}")
    return widget


def add_weather_screen(root):
    from .layout import box, screen
    for mode in ("current", "details", "forecast"):
        forecast = mode == "forecast"
        width, height = (840 if forecast else 340), 104
        name = {"current": "UmbraWeather", "details": "UmbraWeatherDetails", "forecast": "UmbraWeatherForecast"}[mode]
        s = screen(root, name, width, height, 24, 24, backgroundColor="transparent",
                   flags="wfNoBorder,wfModal", zPosition="10")
        box(s, "eLabel", 0, 0, width, height, backgroundColor="UmbraPanel", cornerRadius="8", zPosition="-1")
        weather_icon(s, 10, 18, 72)
        text_width = 210 if forecast else 230
        weather_label(s, 94, 10, text_width, 26, "city", font=18, noWrap="1")
        weather_label(s, 94, 39, text_width, 34, "temperature_current", font=24, noWrap="1")
        if mode != "current":
            weather_label(s, 94, 77, text_width, 21, "temperature_high_low,day1",
                          font=15, foregroundColor="secondary", noWrap="1")
        if forecast:
            for day in range(1, 6):
                x = 322 + (day - 1) * 100
                weather_label(s, x, 8, 96, 22, f"weekshortday,day{day}", font=16, halign="center", noWrap="1")
                weather_icon(s, x + 23, 30, 50, f"day{day}")
                weather_label(s, x, 80, 96, 21, f"temperature_high_low,day{day}", font=15,
                              halign="center", foregroundColor="secondary", noWrap="1")


def apply_weather(root, options):
    for page in root.findall("screen"):
        if page.get("name") not in ("InfoBar", "UmbraBase_InfoBar", "UmbraMedia_InfoBar"):
            continue
        for applet in page.findall("applet"):
            if "UmbraSettings.weather_overlay" in (applet.text or ""):
                applet.text = "from Plugins.Extensions.UmbraSettings.weather_overlay import install\ninstall(self, %r)" % options.get("weatherInfo", "off")
    return root
