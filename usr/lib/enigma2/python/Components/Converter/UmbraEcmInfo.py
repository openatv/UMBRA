"""Umbra ECM summary and CryptoBar colors, using OpenATV's native data."""

import re

from enigma import iServiceInformation
from Components.Converter.Converter import Converter
from Components.Converter.Poll import Poll
from Components.Element import cached
from Components.config import config
from Tools.GetEcmInfo import GetEcmInfo


def crypto_bar_colors(text):
    from skin import colors

    # Both native APIs emit these defaults but accept different parameter types.
    # Color the output only; never change their shared skin.parameters contract.
    roles = {0x0000FF00: "accent", 0x00FFFF00: "foreground",
             0x007F7F7F: "muted", 0x00FFFFFF: "foreground"}

    def replace(match):
        role = roles.get(int(match[1], 16))
        try:
            value = colors[role].argb()
            if type(value) is int and 0 <= value <= 0xFFFFFFFF:
                return r"\c%08x" % value
        except (KeyError, AttributeError, TypeError, ValueError):
            pass
        return match[0]

    return re.sub(r"\\c([0-9a-fA-F]{8})", replace, text or "")


def ecm_time(value):
    value = str(value).strip()
    if re.fullmatch(r"\d+[.,]\d+", value):
        return value.replace(",", ".") + " s"
    if value.isdigit():
        return value + " ms"
    if re.fullmatch(r"\d+(?:[.,]\d+)?\s*(?:msec|ms|s)", value):
        return value
    return ""


def summary(ecm, hide_names=False):
    native, caid, provider, pid = ecm.getEcmData()[:4]
    try:
        if not int(caid, 16):
            return ""
    except (TypeError, ValueError):
        return ""
    protocol = ecm.getInfo("protocol") or ecm.getInfo("using")
    parts = [protocol] if protocol and protocol != "fta" else []
    if hide_names:
        # Native verbose text can include an address or reader even when 'from'
        # is masked. Keep all source names out when the OSD privacy option is set.
        timing = ecm_time(ecm.getInfo("ecm time"))
        if timing:
            parts.append(timing)
        hops = ecm.getInfo("hops")
        if hops.isdigit() and int(hops):
            parts.append("Hops " + hops)
    elif native:
        parts.append(" ".join(native.split()))
    try:
        if int(pid, 16):
            parts.append(f"PID {int(pid, 16):04X}")
    except (TypeError, ValueError):
        pass
    return "ECM: " + "  |  ".join(parts) if parts else ""


class UmbraEcmInfo(Poll, Converter):
    def __init__(self, type):
        Converter.__init__(self, type)
        Poll.__init__(self)
        self.colorize = type == "CryptoBarColors"
        if not self.colorize:
            self.ecm = GetEcmInfo()
            self.poll_interval = 1000
            self.poll_enabled = True

    @cached
    def getText(self):
        if config.usage.show_cryptoinfo.value < 1:
            return ""
        if self.colorize:
            return crypto_bar_colors(self.source.text)
        service = self.source.service
        info = service and service.info()
        if not info or info.getInfo(iServiceInformation.sIsCrypted) != 1:
            return ""
        # Some softcams include a SID. Reject an ECM left over from another
        # service while tuning; older formats without a SID remain supported.
        sid = self.ecm.getInfo("sid")
        if sid:
            try:
                if int(sid, 16) != info.getInfo(iServiceInformation.sSID):
                    return ""
            except ValueError:
                return ""
        return summary(self.ecm, config.softcam.hideServerName.value)

    text = property(getText)
