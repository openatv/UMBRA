"""Optional e2MDB skin contracts; no database access or plugin imports."""

from copy import deepcopy
from pathlib import Path
import xml.etree.ElementTree as ET


PYTHON_ROOT = Path("/usr/lib/enigma2/python")
PLUGIN_MODULE = "Plugins/Extensions/e2MDB/plugin"
CONVERTER_MODULE = "Components/Converter/E2MDBEventInfo"
MEDIA_OPTIONS = {"infobarLayout", "epgArtwork", "channelArtwork"}


def media_available(python_root=PYTHON_ROOT):
    return all(any((python_root / (module + suffix)).is_file() for suffix in (".py", ".pyc"))
               for module in (PLUGIN_MODULE, CONVERTER_MODULE))


def _module_condition(module):
    return "(" + " or ".join(f"isfile('{PYTHON_ROOT.as_posix()}/{module}{suffix}')" for suffix in (".py", ".pyc")) + ")"


MEDIA_CONDITION = " and ".join(
    [_module_condition(module) for module in (PLUGIN_MODULE, CONVERTER_MODULE)] +
    ["config.plugins.e2mdb.enableDatabase.value", "config.plugins.e2mdb.epgMetaEnabled.value"])


def media_condition(screen):
    flag = "epgInfoBarEnabled" if screen == "InfoBar" else "epgChannelSelectionEnabled" if screen.startswith("ChannelSelection") else None
    return MEDIA_CONDITION + (f" and config.plugins.e2mdb.{flag}.value" if flag else "")


def apply_media(root, options, width):
    """Retain native fallback panels so saved media styles survive removal/disable."""
    factor = width / 1280

    def geometry(widget, x, y, w, h):
        widget.set("position", f"{round(x * factor)},{round(y * factor)}")
        widget.set("size", f"{round(w * factor)},{round(h * factor)}")
        return widget

    def meta(parent, source, token, x, y, w, h, image=False, **attrs):
        widget = ET.SubElement(parent, "widget", source=source, render="Pixmap" if image else "Label",
                               transparent="1", **attrs)
        geometry(widget, x, y, w, h)
        if image:
            widget.attrib.update(alphatest="blend", scaleFlags="centerScaled")
        else:
            widget.attrib.update(font=f"Regular;{round(17 * factor)}", foregroundColor="secondary",
                                 valign="center", noWrap="1")
        ET.SubElement(widget, "convert", type="E2MDBEventInfo").text = token
        return widget

    def artwork(parent, source, token, x, y, w, h):
        # The neutral native surface remains useful while the backend has no artwork.
        background = ET.SubElement(parent, "eLabel", backgroundColor="surface", zPosition="0")
        geometry(background, x, y, w, h)
        return meta(parent, source, token, x, y, w, h, image=True, zPosition="2")

    def variant(name, transform):
        page = root.find(f"screen[@name='{name}']")
        if page is None:
            return
        base = ET.Element("screen", name=f"UmbraBase_{name}")
        media = ET.Element("screen", name=f"UmbraMedia_{name}")
        base.extend(deepcopy(list(page)))
        media.extend(deepcopy(list(page)))
        transform(media)
        for child in list(page):
            page.remove(child)
        condition = media_condition(name)
        ET.SubElement(page, "panel", name=base.get("name"), condition="!" + condition)
        ET.SubElement(page, "panel", name=media.get("name"), condition=condition)
        root.extend((base, media))

    def infobar(page):
        backdrop = options["infobarLayout"] == "backdrop"
        for widget in list(page):
            if widget.get("render") == "Picon":
                geometry(widget, 93 if backdrop else 32, 485 if backdrop else 481, 146 if backdrop else 116, 88 if backdrop else 70)
                widget.set("zPosition", "1")
            if widget.get("backgroundColor") == "selection" and widget.tag == "eLabel":
                page.remove(widget)
        x, y, w, h = (24, 449, 284, 160) if backdrop else (24, 417, 132, 198)
        # Cover the picon only when artwork exists, including its letterbox margins.
        layers = (("Image", "HasImage"), ("Backdrop", "HasBackdrop")) if backdrop else (("Cover", "HasCover"),)
        for level, (token, available) in enumerate(layers):
            shade = meta(page, "session.Event_Now", available, x, y, w, h,
                         backgroundColor="surface", zPosition=str(2 + level * 2))
            shade.set("render", "FixedLabel")
            shade.set("text", "")
            shade.set("transparent", "0")
            ET.SubElement(shade, "convert", type="ConditionalShowHide")
            meta(page, "session.Event_Now", token, x, y, w, h, image=True, zPosition=str(3 + level * 2))
        if backdrop:
            for widget in page.findall("widget"):
                pos = widget.get("position", "").split(",")
                size = widget.get("size", "").split(",")
                if len(pos) == 2 and pos[0] in (str(round(198 * factor)), str(round(361 * factor))):
                    widget.set("position", f"{int(pos[0]) + round(136 * factor)},{pos[1]}")
                    if int(size[0]) > round(300 * factor):
                        widget.set("size", f"{int(size[0]) - round(136 * factor)},{size[1]}")
        meta(page, "session.Event_Now", "InfoLine", 334 if backdrop else 198, 440,
             912 if backdrop else 1048, 29, textBorderColor="black", textBorderWidth="1")

    if options.get("infobarLayout", "classic") != "classic":
        variant("InfoBar", infobar)

    def channel(page):
        portrait = options["channelArtwork"] == "cover"
        for widget in list(page):
            if widget.get("render") == "Picon":
                page.remove(widget)
            elif widget.get("source") == "Event":
                types = [c.text for c in widget.findall("convert")]
                if "Name" in types:
                    geometry(widget, 832 if portrait else 680, 90 if portrait else 380, 400 if portrait else 552, 64)
                elif "FullDescription" in types:
                    geometry(widget, 680, 318 if portrait else 516, 552, 306 if portrait else 108)
                elif "Times" in types:
                    geometry(widget, 832 if portrait else 680, 250 if portrait else 450, 200 if portrait else 240, 27)
                elif "Duration" in types:
                    geometry(widget, 1060, 250 if portrait else 450, 172, 27)
        artwork(page, "Event", "Cover" if portrait else "Backdrop", 680, 90, 132 if portrait else 552, 198 if portrait else 276)
        meta(page, "Event", "InfoLine", 832 if portrait else 680, 170 if portrait else 486, 400 if portrait else 552, 54 if portrait else 24)

    if options.get("channelArtwork", "none") != "none":
        for name in ("ChannelSelection", "ChannelSelectionDefault"):
            variant(name, channel)

    def epg(page, compact=False):
        portrait = options["epgArtwork"] == "cover"
        if compact:
            artwork(page, "Event", "Cover" if portrait else "Backdrop", 24, 84, 80 if portrait else 212, 120)
            shift = 92 if portrait else 224
            for widget in page.findall("widget[@source='Event']"):
                if widget.find("convert[@type='EventName']") is not None or widget.find("convert[@type='EventTime']") is not None:
                    x, y = map(int, widget.get("position").split(","))
                    w, h = map(int, widget.get("size").split(","))
                    widget.set("position", f"{x + round(shift * factor)},{y}")
                    if w > round(300 * factor):
                        widget.set("size", f"{w - round(shift * factor)},{h}")
        else:
            artwork(page, "Event", "Cover" if portrait else "Backdrop", 794, 190, 104 if portrait else 450, 156 if portrait else 224)
            meta(page, "Event", "InfoLine", 914 if portrait else 794, 190 if portrait else 422, 330 if portrait else 450, 55 if portrait else 29)
            if portrait:
                genres = meta(page, "Event", "Genres", 914, 256, 330, 80)
                genres.set("noWrap", "0")
            for widget in page.findall("widget[@source='Event']"):
                if any(c.text == "FullDescription" for c in widget.findall("convert")):
                    geometry(widget, 794, 366 if portrait else 458, 450, 266 if portrait else 174)

    def quick_epg(page):
        portrait = options["epgArtwork"] == "cover"
        art_width = 88 if portrait else 216
        artwork(page, "Event", "Cover" if portrait else "Backdrop", 794, 54, art_width, 132)
        for widget in page.findall("widget[@source='Event']"):
            if any(c.text == "FullDescription" for c in widget.findall("convert")):
                geometry(widget, 810 + art_width, 54, 434 - art_width, 138)

    if options.get("epgArtwork", "none") != "none":
        for name in ("EPGSelection", "EPGSearch"):
            variant(name, epg)
        variant("QuickEPG", quick_epg)
        # The graphical Infobar stays a full-width timeline, without an artwork header.
        for name in ("GraphicalEPG", "GraphicalEPGPIG", "EPGSelectionMulti"):
            variant(name, lambda page: epg(page, compact=True))
    return root
