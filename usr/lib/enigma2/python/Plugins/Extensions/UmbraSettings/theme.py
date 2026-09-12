"""Shared by the desktop builder and the receiver settings plugin."""

from .i18n import N_

from pathlib import Path
import os
import tempfile
import xml.etree.ElementTree as ET


PALETTES = {
    "graphite": (N_("Graphite"), "28343b", "13191c", "41535c", "768b94", "607d8a"),
    "midnight": (N_("Midnight"), "1c2532", "0e141d", "304967", "91afcf", "579ee8"),
    "carbon": (N_("Carbon"), "27292c", "121416", "45494e", "aab2bb", "d6dce2"),
    "emerald": (N_("Emerald"), "20312d", "101c18", "33594a", "8dbba4", "60b58f"),
    "petrol": (N_("Petrol"), "203239", "101d22", "315866", "88b9c7", "54bfd4"),
    "bordeaux": (N_("Bordeaux"), "32252a", "1d1217", "62404e", "c49aaa", "d57998"),
    "amber": (N_("Amber"), "302c25", "1c1913", "5c5140", "c5b08b", "d3ac58"),
}
ACCENTS = {"theme": N_("Skin color"), "cyan": N_("Cyan"), "blue": N_("Blue"), "green": N_("Green"),
           "red": N_("Red"), "gold": N_("Gold"), "white": N_("White")}
ACCENT_COLORS = {"cyan": "54bfd4", "blue": "579ee8", "green": "60b58f",
                 "red": "e36464", "gold": "d3ac58", "white": "d6dce2"}
RESOLUTIONS = {"HD": (1280, 720), "FHD": (1920, 1080), "WQHD": (2560, 1440)}
TV_VISIBILITY = {"opaque": N_("Off"), "soft": N_("Subtle"), "balanced": N_("Balanced"), "clear": N_("Clear")}
TV_ALPHA = {"opaque": 0, "soft": 0x30, "balanced": 0x48, "clear": 0x58}
GRADIENTS = {
    "UmbraScreen": "surface,background,surface,vertical",
    "UmbraPanel": "background,surface,vertical",
    "UmbraMenuTile": "background,surface,vertical",
    "UmbraMenuTileSelected": "selection,background,surface,vertical",
    "UmbraRow": "background,rowShade,vertical",
    "UmbraSelection": "selection,background,vertical",
    "UmbraListSelection": "selection,selectionShade,vertical",
    "UmbraFade": "transparent,surface,vertical",
    "UmbraInfoFade": "transparent,overlay,vertical",
    "UmbraInfoShade": "overlay,surface,vertical",
    "UmbraProgress": "muted,accent,horizontal",
    "UmbraVolume": "muted,accent,vertical",
    "UmbraChannelShade": "channelShadeStrong,channelShadeLight,horizontal",
}


def colors(palette="graphite", accent="theme", tv_visibility="balanced"):
    _, background, surface, selected, muted, progress = PALETTES[palette]
    if accent != "theme":
        progress = ACCENT_COLORS[accent]
    result = {"background": "00" + background, "surface": "00" + surface,
              "selection": "00" + selected, "muted": "00" + muted,
              "accent": "00" + progress, "foreground": "00f4f5f6",
              "secondary": "00c1c8cc", "transparent": "ff000000",
              "overlay": "18" + surface, "disabled": "00777c80",
              "recording": "00ffe59a",
              "red": "00e64b50", "green": "006eaf58", "yellow": "00d9b853",
              "blue": "00588eda", "black": "00000000", "white": "00ffffff"}
    alpha = TV_ALPHA[tv_visibility]
    result["rowShade"] = "00" + "".join(f"{(3 * int(background[i:i + 2], 16) + int(surface[i:i + 2], 16)) // 4:02x}"
                                      for i in (0, 2, 4))
    result["selectionShade"] = "00" + "".join(f"{(int(selected[i:i + 2], 16) + int(background[i:i + 2], 16)) // 2:02x}"
                                            for i in (0, 2, 4))
    result.update(channelShadeStrong=f"{alpha // 2:02x}{surface}", channelShadeLight=f"{alpha:02x}{surface}")
    for key in ("red", "green", "yellow", "blue"):
        result["key_" + key] = result[key]
    result.update(key_text=result["foreground"], key_back=result["surface"])
    return {key: "#" + value for key, value in result.items()}


def theme_xml(palette="graphite", accent="theme", tv_visibility="balanced"):
    root = ET.Element("skin")
    node = ET.SubElement(root, "colors")
    for name, value in {**colors(palette, accent, tv_visibility), **GRADIENTS}.items():
        ET.SubElement(node, "color", name=name, value=value)
    ET.indent(root)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def atomic_write(path, data):
    """Keep the previous complete skin readable if a write fails."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
