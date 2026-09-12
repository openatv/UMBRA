from pathlib import Path
import json

from Components.ActionMap import HelpableActionMap
from Components.config import ConfigSelection, ConfigSubsection, ConfigText, config, configfile, getConfigListEntry
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.InputBox import InputBox
from Screens.MessageBox import MessageBox
from Screens.Setup import Setup

from .styles import GROUPS, INHERIT, OPTIONS, export_pack, load_packs, native_layout, prepare_skin, reconcile_native, resolve, skin_resolution
from .theme import RESOLUTIONS
from .media import MEDIA_OPTIONS, media_available
from .i18n import _, ngettext


STYLE_DIR = Path("/etc/enigma2/umbra/styles")


def pack_title(key, pack):
    name = pack["name"]
    return name if key.startswith("user:") else _(name)


PACKS, PACK_ERRORS = load_packs(STYLE_DIR)
config.plugins.umbra = ConfigSubsection()
cfg = config.plugins.umbra
cfg.style = ConfigSelection(default="graphite", choices=[(key, pack_title(key, value)) for key, value in PACKS.items()])
cfg.section = ConfigSelection(default="colors", choices=[(key, _(title)) for key, title in GROUPS.items()])
cfg.nativeSnapshot = ConfigText(default="", fixed_size=False)
cfg.resolution = ConfigSelection(default="HD", choices=[(key, f"{key} ({size[0]} x {size[1]})") for key, size in RESOLUTIONS.items()])
for key, (option_title, option_group, option_default, choices) in OPTIONS.items():
    setattr(cfg, key, ConfigSelection(default=INHERIT, choices=[(INHERIT, _("From style pack")), *((value, _(label)) for value, label in choices.items())]) if choices
            else ConfigText(default="", fixed_size=False, visible_width=12))

NATIVE = {"channelScreen": "screenStyle", "channelRows": "widgetStyle", "showPicon": "showPicon",
          "showNumber": "showNumber", "showServiceTypeIcon": "showServiceTypeIcon", "showCryptoIcon": "showCryptoIcon",
          "piconRatio": "piconRatio", "showTimers": "showTimers", "recordIndicatorMode": "recordIndicatorMode"}


def native_values():
    values = {}
    for key, name in NATIVE.items():
        setting = getattr(config.channelSelection, name, None)
        if setting is not None:
            values[key] = ("on" if setting.value else "off") if isinstance(setting.value, bool) else str(setting.value)
    return values


class UmbraSettings(Setup):
    def __init__(self, session):
        global PACKS, PACK_ERRORS
        PACKS, PACK_ERRORS = load_packs(STYLE_DIR)
        cfg.style.setChoices([(key, pack_title(key, value)) for key, value in PACKS.items()], default="graphite")
        cfg.section.setChoices([(key, _(title)) for key, title in GROUPS.items()])
        for key, (option_title, option_group, option_default, choices) in OPTIONS.items():
            if choices:
                getattr(cfg, key).setChoices([(INHERIT, _("From style pack")), *((value, _(label)) for value, label in choices.items())])
        cfg.resolution.value = skin_resolution(config.skin.primary_skin.value, cfg.resolution.value)
        self.original = {key: getattr(cfg, key).value for key in (*OPTIONS, "style", "section", "resolution")}
        try:
            previous = json.loads(cfg.nativeSnapshot.value) if cfg.nativeSnapshot.value else {}
            if not isinstance(previous, dict):
                previous = {}
        except ValueError:
            previous = {}
        effective = resolve(PACKS[cfg.style.value], self.overrides())
        for key, value in reconcile_native(self.overrides(), native_values(), previous, effective).items():
            getattr(cfg, key).value = value
        Setup.__init__(self, session, setup="Umbra", plugin="Extensions/UmbraSettings", PluginLanguageDomain="Umbra")
        self["key_yellow"] = StaticText(_("Style defaults"))
        self["key_blue"] = StaticText(_("Save style"))
        self["styleActions"] = HelpableActionMap(self, ["ColorActions"], {
            "yellow": (self.resetOverrides, _("Reset personal overrides to style defaults")),
            "blue": (self.exportStyle, _("Save the current appearance as a personal style pack"))
        }, prio=-2)
        if PACK_ERRORS:
            self.onShown.append(self.showPackErrors)

    def overrides(self):
        return {key: getattr(cfg, key).value for key in OPTIONS}

    def createSetup(self, appendItems=None, prependItems=None):
        pack = PACKS.get(cfg.style.value, PACKS["graphite"])
        rows = [getConfigListEntry(_("Style pack"), cfg.style, _("Style defaults and personal overrides are stored separately.")),
                getConfigListEntry(_("Section"), cfg.section), getConfigListEntry(_("OSD resolution"), cfg.resolution,
                _("Use WQHD only with a supported framebuffer. Style packs do not change the resolution."))]
        for key, (title, group, option_default, choices) in OPTIONS.items():
            if group != cfg.section.value:
                continue
            if key in MEDIA_OPTIONS and not media_available():
                continue
            value = pack["options"][key]
            description = _("Style value: %s") % (_(choices[value]) if choices else value or _("From color palette"))
            if key in MEDIA_OPTIONS:
                description += ". " + _("Without active e2MDB metadata, the base layout is retained.")
            if key == "tunerInfo":
                description += ". " + _("Native tuner allocation, SNR, AGC and BER; OpenATV reports unavailable values.")
            if key == "cryptoInfo":
                description += ". " + _("Status, CA system, CAID and provider ID. CA details follow the OpenATV encryption information setting.")
            if key == "weatherInfo":
                description += ". " + _("Location, provider, units and update interval are configured only in OAWeather. The display stays hidden without weather data.")
            if choices is None:
                description += ". " + _("Leave empty for the style value, otherwise enter six RGB hexadecimal digits.")
            title = _("%s (RGB)") % _(title[:-6]) if key.startswith("color_") else _(title)
            rows.append(getConfigListEntry(title, getattr(cfg, key), description))
        self.list = rows
        self["config"].setList(rows)
        self.setTitle("Umbra / " + pack_title(cfg.style.value, pack))
        self.setFootnote(None)

    def setFootnote(self, footnote):
        if "footnote" in self:
            count = sum(getattr(cfg, key).value not in (INHERIT, "") for key in OPTIONS)
            self["footnote"].setText(footnote or ngettext("%d personal override", "%d personal overrides", count) % count)
            self["footnote"].show()

    def showPackErrors(self):
        self.onShown.remove(self.showPackErrors)
        self.session.open(MessageBox, _("Style packs not loaded:\n") + "\n".join(PACK_ERRORS), type=MessageBox.TYPE_ERROR)

    def resetOverrides(self):
        self.session.openWithCallback(self.resetConfirmed, MessageBox,
            _("Replace all personal overrides with the selected style defaults?"), type=MessageBox.TYPE_YESNO, default=False)

    def resetConfirmed(self, answer):
        if answer:
            for key, entry in OPTIONS.items():
                getattr(cfg, key).value = INHERIT if entry[3] else ""
            self.createSetup()

    def exportStyle(self):
        self.session.openWithCallback(self.exportNamed, InputBox, title=_("Style pack name"), text=_("My Umbra"), maxSize=False)

    def exportNamed(self, name):
        if not name:
            return
        if not 1 <= len(name.strip()) <= 80:
            self.session.open(MessageBox, _("The name is too long"), type=MessageBox.TYPE_ERROR)
            return
        import hashlib
        target = STYLE_DIR / ("style-" + hashlib.sha256(name.strip().encode()).hexdigest()[:12] + ".json")
        if target.exists():
            self.session.openWithCallback(lambda answer: self.writeExport(target, name.strip()) if answer else None,
                MessageBox, _("Replace this style pack?"), type=MessageBox.TYPE_YESNO, default=False)
        else:
            self.writeExport(target, name.strip())

    def writeExport(self, path, name):
        global PACKS
        try:
            export_pack(path, name, resolve(PACKS[cfg.style.value], self.overrides()))
            PACKS, errors = load_packs(STYLE_DIR)
            cfg.style.setChoices([(key, pack_title(key, value)) for key, value in PACKS.items()])
            self.session.open(MessageBox, _("Style pack saved: %s") % name, type=MessageBox.TYPE_INFO)
        except (OSError, ValueError) as error:
            self.session.open(MessageBox, _("Could not save style pack: %s") % error, type=MessageBox.TYPE_ERROR)

    def keySave(self):
        if getattr(self, "applying", False):
            return
        from enigma import eTimer
        from Screens.Processing import Processing
        self.applying = True
        Processing.instance.setDescription(_("Applying Umbra..."))
        Processing.instance.showProgress(endless=True)
        self.applyTimer = eTimer()
        self.applyTimer.callback.append(self.applyPending)
        self.applyTimer.start(100, True)

    def applyPending(self):
        from Screens.Processing import Processing
        try:
            self.applyChanges()
        finally:
            Processing.instance.hideProgress()
            self.applying = False

    def applyChanges(self):
        selected = cfg.resolution.value
        try:
            options = resolve(PACKS[cfg.style.value], self.overrides())
            # Native grids require their own item geometry; keep the saved user preference.
            options = native_layout(options)
            prepare_skin(Path("/usr/share/enigma2/Umbra"), options, selected)
        except (OSError, ValueError) as error:
            self.session.open(MessageBox, _("Could not save Umbra: %s") % error, type=MessageBox.TYPE_ERROR)
            return
        for key in (*OPTIONS, "style", "section", "resolution"):
            getattr(cfg, key).save()
        for key, native_name in NATIVE.items():
            setting = getattr(config.channelSelection, native_name, None)
            if setting is not None:
                setting.value = options[key] == "on" if options[key] in ("on", "off") else int(options[key]) if isinstance(setting.value, int) else options[key]
                setting.save()
        cfg.nativeSnapshot.value = json.dumps(native_values(), sort_keys=True)
        cfg.nativeSnapshot.save()
        config.skin.primary_skin.value = f"Umbra/{selected}/skin.xml"
        config.skin.primary_skin.save()
        configfile.save()
        self.original = {key: getattr(cfg, key).value for key in self.original}
        try:
            from skin import reloadSkins
            from Screens.ChannelSelection import ChannelSelection, ChannelSelectionSetup
            if not callable(getattr(self.session, "reloadDialogs", None)):
                raise RuntimeError(_("This Enigma2 version does not support live skin reload."))
            reloadSkins()
            from Components.PluginComponent import plugins
            for plugin in plugins.getPlugins(PluginDescriptor.WHERE_SKINCHANGE):
                plugin(session=self.session)
            exclude = {id(dialog) for dialog in self.session.allDialogs if isinstance(dialog, ChannelSelection)}
            self.session.reloadDialogs(exclude=exclude)
            ChannelSelectionSetup.updateSettings(self.session, force=True)
        except Exception as error:
            print(f"[Umbra] Live skin reload failed: {error}")
            self.session.openWithCallback(self.restart, MessageBox,
                _("Style saved, but live reload did not finish: %s\nRestart the GUI?") % error,
                type=MessageBox.TYPE_YESNO, default=False)
            return
        self.close(True)

    def keyCancel(self):
        if getattr(self, "applying", False):
            return
        for key, value in self.original.items():
            getattr(cfg, key).value = value
        self.close()

    def closeRecursive(self):
        if getattr(self, "applying", False):
            return
        for key, value in self.original.items():
            getattr(cfg, key).value = value
        self.close(True)

    def restart(self, answer):
        if answer:
            from Screens.Standby import TryQuitMainloop
            self.session.open(TryQuitMainloop, 3)
        self.close()


def main(session, **kwargs):
    session.open(UmbraSettings)


def plugin_icon(width=None):
    if width is None:
        from enigma import getDesktop
        width = getDesktop(0).size().width()
    return "plugin_fhd.png" if width >= 1920 else "plugin.png"


def refresh_plugin_icon(session=None, **kwargs):
    from Components.PluginComponent import plugins
    for descriptor in plugins.getPlugins(PluginDescriptor.WHERE_PLUGINMENU):
        if descriptor.function == main:
            descriptor.iconString = plugin_icon()


def Plugins(**kwargs):
    return [PluginDescriptor(name="Umbra", description=_("Style packs and personal appearance"), where=PluginDescriptor.WHERE_PLUGINMENU,
                             icon=plugin_icon(), needsRestart=False, fnc=main),
            PluginDescriptor(where=PluginDescriptor.WHERE_SKINCHANGE, needsRestart=False, fnc=refresh_plugin_icon)]
