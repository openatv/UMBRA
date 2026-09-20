"""Optional native diagnostic panels, shared by all Infobar media variants."""

import xml.etree.ElementTree as ET


def add_lite_infobar(root):
    from .layout import box, convert, event, label, node, picon, progress, screen

    page = screen(root, "InfoBarLite", backgroundColor="transparent",
                  ignoreWidgets="key_red,key_green,key_yellow,key_blue")
    box(page, "eLabel", 24, 584, 1232, 112, backgroundColor="UmbraPanel", cornerRadius="8")
    picon(page, "session.CurrentService", 38, 601, 108, 65).set("zPosition", "1")
    convert(label(page, 166, 594, 878, 28, source="session.CurrentService", font=18, noWrap="1",
                  foregroundColor="secondary"), "ServiceName", "Name")
    event(page, "session.Event_Now", 166, 628, 878, 32, font=22, noWrap="1")
    remaining = convert(label(page, 1068, 628, 168, 28, source="session.Event_Now", font=18,
                              noWrap="1", halign="right", foregroundColor="secondary"), "EventTime", "Remaining")
    convert(remaining, "RemainingToText", "Default")
    convert(label(page, 1120, 594, 116, 28, source="global.CurrentTime", font=20,
                  noWrap="1", halign="right"), "ClockToText", "Default")
    progress(page, "session.Event_Now", 166, 674, 1070, 4)
    recording = box(page, "widget", 1086, 602, 12, 12, source="session.RecordState", render="FixedLabel",
                    text="", backgroundColor="red", cornerRadius="6")
    convert(recording, "ConditionalShowHide", "Blink")
    node(page, "applet", type="onLayoutFinish").text = "from Plugins.Extensions.UmbraSettings.picon_refresh import prime_picons\nprime_picons(self)"


def add_second_infobars(root):
    from .layout import box, convert, event, label, node, picon, progress, screen

    # Both modes use the same event components and native paging/timer actions.
    body = node(root, "screen", name="UmbraSecondInfoBody")
    node(body, "panel", name="UmbraHeader")
    label(body, 30, 104, 1220, 44, name="channel", font=30)
    label(body, 30, 173, 800, 410, name="epg_description", font=22, valign="top")
    progress(body, "session.Event_Now", 30, 637, 1220)
    node(body, "panel", name="UmbraKeys")
    node(body, "applet", type="onLayoutFinish").text = "from Plugins.Extensions.UmbraSettings.picon_refresh import prime_picons\nprime_picons(self)"

    info = screen(root, "SecondInfoBar", ignoreWidgets="FullDescription")
    node(info, "panel", name="UmbraSecondInfoBody")
    picon(info, "session.CurrentService", 890, 175, 320, 210)
    event(info, "session.Event_Next", 880, 430, 350, 100, "Name", 24)

    ecm = screen(root, "SecondInfoBarECM", ignoreWidgets="FullDescription")
    node(ecm, "panel", name="UmbraSecondInfoBody")
    box(ecm, "eLabel", 866, 169, 384, 442, backgroundColor="UmbraPanel", cornerRadius="8")
    picon(ecm, "session.CurrentService", 932, 181, 252, 144)
    label(ecm, 882, 338, 352, 30, text="ECM / CA", font=22)
    for text, inverse in (("Encrypted", ""), ("Free to air", "Invert")):
        status = label(ecm, 882, 374, 352, 28, text=text, source="session.CurrentService", font=18)
        status.set("render", "FixedLabel")
        convert(convert(status, "ServiceInfo", "IsCrypted"), "ConditionalShowHide", inverse)
    convert(label(ecm, 882, 410, 352, 32, source="session.CurrentService", font=18, noWrap="1",
                  foregroundColor="secondary"), "PliExtraInfo", "CryptoSpecial")
    convert(label(ecm, 882, 451, 352, 128, source="session.CurrentService", font=18, valign="top",
                  foregroundColor="secondary"), "CryptoInfo", "VerboseInfo")
    hint = label(ecm, 882, 410, 352, 148, text="Crypto information is disabled in the OpenATV OSD settings.",
                 source="global.CurrentTime", font=18, valign="top", foregroundColor="muted")
    hint.set("render", "FixedLabel")
    convert(convert(hint, "ConfigEntryTest", "config.usage.show_cryptoinfo,0"), "ConditionalShowHide")


def add_diagnostics(root, icons):
    from .layout import convert, icon, label, node

    panel = node(root, "screen", name="UmbraTunerSignals")
    label(panel, 0, 0, 62, 28, text="Tuner", font=16, foregroundColor="muted")
    convert(label(panel, 66, 0, 134, 28, source="session.FrontendInfo", font=16, noWrap="1"), "FrontendInfo", "STRING")
    # The transponder system, not tuner capability, distinguishes DVB-T from T2.
    for system, glyph in (("DVB-S", "satellite_alt"), ("DVB-S2", "satellite_alt"),
                          ("DVB-T", "settings_input_antenna"), ("DVB-T2", "settings_input_antenna"),
                          ("DVB-T/T2", "settings_input_antenna"), ("DVB-C", "cable"), ("ATSC", "settings_input_antenna")):
        converters = (("TransponderInfo", system), ("ConditionalShowHide", ""))
        icon(panel, icons, glyph, 304, 0, 22, color="foreground", source="session.CurrentService", converters=converters)
        text = label(panel, 336, 0, 116, 28, text=system, source="session.CurrentService", font=16, noWrap="1")
        text.set("render", "FixedLabel")
        for kind, value in converters:
            convert(text, kind, value)
    # DAB can arrive over a DVB transport. Keep its service badge in a separate slot.
    icon(panel, icons, "radio", 210, 0, 22, color="foreground", source="session.CurrentService",
         converters=(("ServiceInfo", "IsDAB"), ("ConditionalShowHide", "")))
    dab = label(panel, 240, 0, 60, 28, text="DAB+", source="session.CurrentService", font=16, noWrap="1")
    dab.set("render", "FixedLabel")
    convert(convert(dab, "ServiceInfo", "IsDAB"), "ConditionalShowHide")
    for title, token, x, w in (("SNR", "SNRdB", 474, 116), (None, "SNR", 654, 100),
                               ("AGC", "AGC", 798, 100), ("BER", "BER", 1012, 158)):
        if title:
            label(panel, x, 0, 50, 28, text=title, font=16, foregroundColor="muted")
        convert(label(panel, x + (54 if title else 0), 0, w, 28, source="session.FrontendStatus", font=16, noWrap="1"), "FrontendInfo", token)

    panel = node(root, "screen", name="UmbraTunerTransponder")
    convert(label(panel, 0, 0, 1232, 28, source="session.CurrentService", font=16, noWrap="1",
                  foregroundColor="secondary"), "TransponderInfo")

    panel = node(root, "screen", name="UmbraCryptoInfo")
    # CA name already indicates encryption/FTA; the status strip keeps its lock
    # icon. Reuse the width for ECM details instead of adding a second row.
    for token, x, w in (("CryptoSpecial", 0, 300), ("CryptoBar", 982, 250)):
        convert(label(panel, x, 0, w, 28, source="session.CurrentService", font=16, noWrap="1",
                      foregroundColor="secondary"), "PliExtraInfo", token)
    convert(label(panel, 310, 0, 658, 28, source="session.CurrentService", font=16, noWrap="1",
                  foregroundColor="secondary"), "UmbraEcmInfo", "Summary")
    hint = label(panel, 0, 0, 1232, 28, source="global.CurrentTime", font=16, noWrap="1",
                 text="Crypto information is disabled in the OpenATV OSD settings.", foregroundColor="muted")
    hint.set("render", "FixedLabel")
    convert(convert(hint, "ConfigEntryTest", "config.usage.show_cryptoinfo,0"), "ConditionalShowHide")


def apply_diagnostics(root, options, width):
    rows = []
    if options.get("tunerInfo", "off") != "off":
        rows.append("UmbraTunerSignals")
    if options.get("tunerInfo") == "details":
        rows.append("UmbraTunerTransponder")
    if options.get("cryptoInfo", "off") == "on":
        rows.append("UmbraCryptoInfo")
    if not rows:
        return root
    factor = width / 1280
    shift = round(len(rows) * 32 * factor)
    for page in root.findall("screen"):
        if page.get("name") not in ("InfoBar", "UmbraBase_InfoBar", "UmbraMedia_InfoBar"):
            continue
        # Media branch selectors have no widgets: adjust the selected branches only.
        if not page.findall("widget"):
            continue
        for widget in page:
            position = widget.get("position", "").split(",")
            if len(position) != 2 or not all(value.lstrip("-").isdigit() for value in position):
                continue
            x, y = map(int, position)
            if round(414 * factor) <= y < round(674 * factor):
                widget.set("position", f"{x},{y - shift}")
                if widget.get("backgroundColor") == "UmbraInfoShade":
                    w, h = map(int, widget.get("size").split(","))
                    widget.set("size", f"{w},{h + shift}")
        for i, name in enumerate(rows):
            ET.SubElement(page, "panel", name=name,
                          position=f"{round(24 * factor)},{round((673 - len(rows) * 32 + i * 32) * factor)}",
                          size=f"{round(1232 * factor)},{round(28 * factor)}")
    return root
