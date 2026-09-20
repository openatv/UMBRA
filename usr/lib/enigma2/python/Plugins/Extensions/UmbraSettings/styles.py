"""Declarative style packs with independently stored user overrides.

Shared by builder and receiver; packs are validated JSON data, never Python.
Resolution is deliberately a receiver setting, not part of a transferable pack.
"""

from copy import deepcopy
import ast
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from .theme import ACCENTS, PALETTES, TV_VISIBILITY, GRADIENTS, RESOLUTIONS, atomic_write, colors
from .compact import compact_screens
from .media import apply_media
from .infobar import apply_diagnostics
from .weather import apply_weather
from .i18n import _, N_


INHERIT = "inherit"
GROUPS = {"colors": N_("Colors"), "layout": N_("Layout"), "infobar": N_("Infobar"), "channels": N_("Channel list")}
OPTIONS = {
    "palette": (N_("Color palette"), "colors", "graphite", {k: v[0] for k, v in PALETTES.items()}),
    "accent": (N_("Progress color"), "colors", "theme", ACCENTS),
    "tvVisibility": (N_("TV picture behind details"), "colors", "balanced", TV_VISIBILITY),
    "gradients": (N_("Gradients"), "layout", "on", {"on": N_("On"), "off": N_("Solid color")}),
    "corners": (N_("Selection corners"), "layout", "8", {"0": N_("Square"), "4": "4 px", "8": "8 px"}),
    "fontScale": (N_("Text size"), "layout", "100", {str(x): f"{x} %" for x in (90, 95, 100, 105)}),
    "menuWidth": (N_("Menu width"), "layout", "470", {"470": N_("Standard"), "560": N_("Wide")}),
    "showClock": (N_("Clock in menus"), "layout", "on", {"on": N_("On"), "off": N_("Off")}),
    "progressHeight": (N_("Progress bar thickness"), "layout", "5", {"3": N_("Thin"), "5": N_("Standard"), "7": N_("Wide")}),
    "eventDescription": (N_("Extended event description"), "infobar", "on", {"on": N_("On"), "off": N_("Off")}),
    "technicalInfo": (N_("Video and audio information"), "infobar", "on", {"on": N_("On"), "off": N_("Off")}),
    "tunerInfo": (N_("Tuner and signal information"), "infobar", "off", {"off": N_("Off"), "signal": N_("Tuner / SNR / AGC / BER"), "details": N_("With transponder details")}),
    "cryptoInfo": (N_("Encryption / ECM information"), "infobar", "off", {"off": N_("Off"), "on": N_("On")}),
    "weatherInfo": (N_("Weather at top left"), "infobar", "off", {"off": N_("Off"), "current": N_("Current"), "details": N_("With daily values"), "forecast": N_("With five-day forecast")}),
    "serviceIcons": (N_("Status icons"), "infobar", "all", {"all": N_("All, inactive dimmed"), "active": N_("Active only"), "off": N_("Off")}),
    "infobarLayout": (N_("Infobar layout"), "infobar", "classic", {"classic": N_("Classic"), "cover": N_("Cover"), "backdrop": N_("Panorama")}),
    "epgArtwork": (N_("EPG artwork"), "infobar", "none", {"none": N_("Off"), "cover": N_("Cover"), "backdrop": N_("Panorama")}),
    "channelArtwork": (N_("Artwork in details"), "channels", "none", {"none": N_("Off"), "cover": N_("Cover"), "backdrop": N_("Panorama")}),
    "channelScreen": (N_("View"), "channels", "ChannelSelectionDefault", {"ChannelSelectionDefault": N_("Details"), "ChannelSelectionPIG": N_("Live TV preview"), "ChannelSelectionFull": N_("Full screen"), "ChannelSelectionGrid": N_("Gallery"), "ChannelSelectionColumns": N_("Columns")}),
    "channelRows": (N_("Rows"), "channels", "Default", {"Default": N_("Standard"), "Compact": N_("Compact"), "Extended": N_("Extended"), "Gallery": N_("Gallery"), "Columns": N_("Columns")}),
    "showPicon": (N_("Picons"), "channels", "on", {"on": N_("On"), "off": N_("Off")}),
    "showNumber": (N_("Channel numbers"), "channels", "on", {"on": N_("On"), "off": N_("Off")}),
    "showServiceTypeIcon": (N_("Reception type"), "channels", "on", {"on": N_("On"), "off": N_("Off")}),
    "showCryptoIcon": (N_("Encryption"), "channels", "on", {"on": N_("On"), "off": N_("Off")}),
    "piconRatio": (N_("Picon aspect ratio"), "channels", "167", {"167": "XPicon / ZZZPicon", "235": "ZZPicon", "250": "ZPicon"}),
    "showTimers": (N_("Show timers"), "channels", "off", {"on": N_("On"), "off": N_("Off")}),
    "recordIndicatorMode": (N_("Recording indicator"), "channels", "2", {"0": N_("Off"), "1": N_("Icon"), "2": N_("Text color")}),
}
CUSTOM_COLORS = {"background": N_("Background"), "surface": N_("Surfaces"), "selection": N_("Selection"), "foreground": N_("Primary text"),
                 "secondary": N_("Secondary text"), "muted": N_("Muted text"), "accent": N_("Accent"), "recording": N_("Recording text"), "red": N_("Red"), "green": N_("Green"), "yellow": N_("Yellow"), "blue": N_("Blue")}
for key, label in CUSTOM_COLORS.items():
    OPTIONS["color_" + key] = (label + " (RGB)", "colors", "", None)

BASE = {key: entry[2] for key, entry in OPTIONS.items()}
PACKS = {
    "graphite": {"version": 1, "name": N_("Umbra Graphite"), "options": dict(BASE)},
    "cinema": {"version": 1, "name": N_("Umbra Cinema"), "options": {**BASE, "palette": "carbon", "tvVisibility": "clear", "technicalInfo": "off", "showClock": "off"}},
    "petrol": {"version": 1, "name": N_("Umbra Petrol"), "options": {**BASE, "palette": "petrol", "accent": "cyan", "channelRows": "Extended"}},
    "clear": {"version": 1, "name": N_("Umbra Clear"), "options": {**BASE, "palette": "carbon", "tvVisibility": "opaque", "gradients": "off", "fontScale": "105", "menuWidth": "560", "progressHeight": "7"}},
    "gallery": {"version": 1, "name": N_("Umbra Gallery"), "options": {**BASE, "palette": "petrol", "infobarLayout": "cover", "epgArtwork": "cover", "channelArtwork": "backdrop", "channelScreen": "ChannelSelectionGrid", "channelRows": "Gallery"}},
}


def validate_options(options, overrides=False):
    if not isinstance(options, dict) or set(options) - set(OPTIONS):
        raise ValueError(_("Unknown style options"))
    result = {}
    for key, value in options.items():
        if not isinstance(value, str):
            raise ValueError(_("%s: expected a text value") % key)
        if overrides and value in (INHERIT, ""):
            continue
        choices = OPTIONS[key][3]
        if choices is not None and value not in choices:
            raise ValueError(_("%s: invalid value %r") % (key, value))
        if choices is None and value and not re.fullmatch(r"#?[0-9a-fA-F]{6}", value):
            raise ValueError(_("%s: expected six RGB hexadecimal digits") % key)
        result[key] = value.lower().removeprefix("#") if choices is None else value
    return result


def load_packs(directory=None):
    packs, errors = deepcopy(PACKS), []
    if directory and Path(directory).is_dir():
        for path in sorted(Path(directory).glob("*.json")):
            try:
                if path.stat().st_size > 65536:
                    raise ValueError(_("File too large"))
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("version") != 1 or not isinstance(data.get("name"), str) or not 1 <= len(data["name"]) <= 80:
                    raise ValueError(_("Invalid style format or name"))
                options = validate_options(data.get("options"))
                packs["user:" + path.stem] = {"version": 1, "name": data["name"], "options": {**BASE, **options}}
            except (OSError, ValueError, TypeError, AttributeError) as error:
                errors.append(f"{path.name}: {error}")
    return packs, errors


def resolve(pack, overrides=None):
    return {**BASE, **validate_options(pack["options"]), **validate_options(overrides or {}, overrides=True)}


def native_layout(options):
    result = dict(options)
    paired = {"ChannelSelectionGrid": "Gallery", "ChannelSelectionColumns": "Columns"}
    if result["channelScreen"] in paired:
        result["channelRows"] = paired[result["channelScreen"]]
    elif result["channelRows"] in paired.values():
        result["channelRows"] = "Default"
    return result


def reconcile_native(overrides, current, previous, effective):
    """Adopt changes made in OpenATV's channel menu without pinning unchanged defaults."""
    result = dict(overrides)
    for key, value in current.items():
        if key in OPTIONS and value in (OPTIONS[key][3] or {}) and value != previous.get(key, effective[key]):
            result[key] = value
    return result


def scale_template_fonts(expression, factor):
    tree = ast.parse(expression.strip(), mode="eval")
    for call in ast.walk(tree):
        if (isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "gFont"
                and len(call.args) >= 2 and isinstance(call.args[0], ast.Constant)
                and call.args[0].value in ("Regular", "Bold") and isinstance(call.args[1], ast.Constant)
                and isinstance(call.args[1].value, (int, float))):
            call.args[1].value = round(call.args[1].value * factor)
    return ast.unparse(tree)


def theme_for(options):
    data = colors(options["palette"], options["accent"], options["tvVisibility"])
    for key in CUSTOM_COLORS:
        value = options["color_" + key]
        if value:
            data[key] = "#00" + value
    def blend(a, b, weight):
        return "#00" + "".join(f"{round(int(data[a][i:i+2], 16) * weight + int(data[b][i:i+2], 16) * (1-weight)):02x}" for i in (3, 5, 7))
    data["rowShade"] = blend("background", "surface", .75)
    data["selectionShade"] = blend("selection", "background", .5)
    for key in ("overlay", "channelShadeStrong", "channelShadeLight"):
        data[key] = data[key][:3] + data["surface"][3:]
    for key in ("red", "green", "yellow", "blue"):
        data["key_" + key] = data[key]
    data.update(key_text=data["foreground"], key_back=data["surface"])
    gradients = dict(GRADIENTS)
    if options["gradients"] == "off":
        for name, value in gradients.items():
            first = value.split(",")[0]
            # Edge fades retain transparency; flat panels and selections remain native fills.
            if first != "transparent":
                gradients[name] = first + "," + first + ",vertical"
    root = ET.Element("skin")
    group = ET.SubElement(root, "colors")
    for name, value in {**data, **gradients}.items():
        ET.SubElement(group, "color", name=name, value=value)
    return xml_bytes(root)


def xml_bytes(root):
    ET.indent(root)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def apply_layout(root, options, width):
    result = apply_media(deepcopy(root), options, width)
    result = apply_diagnostics(result, options, width)
    factor = width / 1280
    for element in result.iter():
        if element.get("itemCornerRadiusSelected") is not None and element.get("itemCornerRadiusSelected") != "0":
            element.set("itemCornerRadiusSelected", str(round(int(options["corners"]) * factor)))
        if element.tag == "rectangle" and element.get("cornerRadius") is not None:
            element.set("cornerRadius", str(round(int(options["corners"]) * factor)))
        for key in list(element.attrib):
            if key in ("font", "fonts") or "Font" in key:
                element.set(key, re.sub(r"(Regular|Bold);(\d+)", lambda m: m[1] + ";" + str(round(int(m[2]) * int(options["fontScale"]) / 100)), element.get(key)))
        if element.tag == "alias" and element.get("font") in ("Regular", "Bold") and element.get("size"):
            element.set("size", str(round(int(element.get("size")) * int(options["fontScale"]) / 100)))
        if element.tag == "parameter" and element.get("name") == "VirtualKeyboardNativeGeometry":
            gap, _, border = element.get("value").split(",")
            element.set("value", f"{gap},{round(int(options['corners']) * factor)},{border}")
        if element.tag == "convert" and element.get("type") == "TemplatedMultiContent" and options["fontScale"] != "100":
            element.text = scale_template_fonts(element.text, int(options["fontScale"]) / 100)
        if options["gradients"] == "off":
            for key in ("foregroundColor", "backgroundColor"):
                value = element.get(key, "").split(",")
                if len(value) >= 3 and value[-1] in ("horizontal", "vertical") and value[0] != "transparent":
                    element.set(key, value[0])
        if element.get("render") == "Progress" and element.get("size"):
            w, h = element.get("size").split(",")
            if h.isdecimal() and int(h) <= round(12 * factor):
                element.set("size", f"{w},{round(int(options['progressHeight']) * factor)}")
    if options["showClock"] == "off":
        for page in result.findall("screen"):
            if page.get("name") not in ("InfoBar", "UmbraBase_InfoBar", "UmbraMedia_InfoBar"):
                for clock in page.findall(".//widget[@source='global.CurrentTime']"):
                    clock.set("size", "0,0")
    infobars = [page for page in result.findall("screen") if page.get("name") in ("InfoBar", "UmbraBase_InfoBar", "UmbraMedia_InfoBar")]
    status = result.find("screen[@name='UmbraServiceStatus']")
    if status is not None:
        mode = options.get("serviceIcons", "all")
        for element in status:
            if mode == "off" or mode == "active" and element.tag == "eLabel":
                element.set("size", "0,0")
    for infobar in infobars:
        for element in infobar.iter("widget"):
            types = [(c.get("type"), (c.text or "").strip()) for c in element.findall("convert")]
            if options["eventDescription"] == "off" and ("EventName", "ExtendedDescription") in types or options["technicalInfo"] == "off" and any(t in ("VAudioInfo", "ServiceInfo") and v in ("AudioCodec", "VideoInfo") for t, v in types):
                element.set("size", "0,0")
    menu = result.find("screen[@name='Menu']")
    if menu is not None and options["menuWidth"] != "470":
        extra = round((int(options["menuWidth"]) - 470) * factor)
        for element in menu.iter():
            size = element.get("size", "")
            if re.fullmatch(r"\d+,\d+", size):
                w, h = map(int, size.split(","))
                if w >= round(300 * factor):
                    element.set("size", f"{w + extra},{h}")
                elif element.get("backgroundColor") in ("red", "green", "yellow", "blue") or element.get("source", "").startswith("key_"):
                    x, y = map(int, element.get("position").split(","))
                    element.set("position", f"{x + (extra // 2 if x >= round(235 * factor) else 0)},{y}")
                    element.set("size", f"{w + extra // 2},{h}")
    return apply_weather(result, options)


def prepare_skin(target, options, resolution):
    """Prepare the chosen resolution transactionally; retain inactive variants unchanged."""
    if resolution not in RESOLUTIONS:
        raise ValueError(_("Unknown resolution"))
    writes = {target / "theme.xml": theme_for(options)}
    native = target / "baseline/native.xml"
    if native.exists():
        writes[target / "native.xml"] = xml_bytes(apply_layout(ET.parse(native).getroot(), options, 1280))
    width, height = RESOLUTIONS[resolution]
    for filename in ("skin.xml", "skinTemplates.xml"):
        baseline = target / "baseline" / resolution / filename
        try:
            root = ET.parse(baseline).getroot()
        except ET.ParseError as error:
            raise ValueError(_("Invalid skin baseline %s/%s: %s") % (resolution, filename, error)) from error
        styled = apply_layout(root, options, width)
        if filename == "skin.xml":
            screens = ET.Element("skin")
            for element in list(styled):
                if element.tag == "screen":
                    screens.append(element)
                    styled.remove(element)
            screens, compact_report = compact_screens(screens, "UmbraPart_")
            styled.extend(screens)
        writes[target / resolution / filename] = xml_bytes(styled)
        # The top-level skin remains the FHD entry point, never an alias to HD/WQHD.
        if resolution == "FHD":
            writes[target / filename] = writes[target / resolution / filename]
    previous = {path: path.read_bytes() if path.exists() else None for path in writes}
    completed = []
    try:
        for path, data in writes.items():
            atomic_write(path, data)
            completed.append(path)
    except OSError:
        for path in reversed(completed):
            if previous[path] is not None:
                atomic_write(path, previous[path])
            else:
                path.unlink(missing_ok=True)
        raise


def skin_resolution(primary_skin, fallback):
    paths = {f"Umbra/{name}/skin.xml": name for name in RESOLUTIONS}
    paths["Umbra/skin.xml"] = "FHD"
    return paths.get(primary_skin, fallback)


def prepare_saved_skin(target, settings, style_directory):
    values = dict(line.split("=", 1) for line in settings.read_text(encoding="utf-8").splitlines() if "=" in line)
    prefix = "config.plugins.umbra."
    # A first installation keeps the build defaults and never activates the skin.
    if not any(key.startswith(prefix) for key in values):
        return False
    packs, errors = load_packs(style_directory)
    key = values.get(prefix + "style", "graphite")
    if key not in packs:
        raise ValueError(_("Saved style pack is missing: %s") % key + ("; " + "; ".join(errors) if errors else ""))
    overrides = {name: values[prefix + name] for name in OPTIONS if prefix + name in values}
    resolution = skin_resolution(values.get("config.skin.primary_skin"), values.get(prefix + "resolution", "HD"))
    prepare_skin(target, resolve(packs[key], overrides), resolution)
    return True


def export_pack(path, name, options):
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
        raise ValueError(_("Style names must contain 1 to 80 characters"))
    data = {"version": 1, "name": name.strip(), "options": {**BASE, **validate_options(options)}}
    atomic_write(path, json.dumps(data, indent=2, ensure_ascii=True).encode())
