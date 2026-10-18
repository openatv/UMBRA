"""Umbra-only dialog geometry and display-text preparation."""

from enigma import ePoint, eSize, eWindow


class BitrateLayout:
	@staticmethod
	def dock(screen):
		if not getattr(screen, "infobar_mode", False):
			return
		from Screens.InfoBar import InfoBar  # InfoBar imports plugins during startup.

		width = screen.desktop.size().width()
		factor = width / 1280
		top = round(440 * factor)
		infoBar = InfoBar.instance
		for widget in getattr(infoBar, "additionalWidgets", ()):
			if dict(widget.skinAttributes).get("backgroundColor") == "UmbraInfoFade":
				top = widget.instance.position().y() + round(26 * factor)
				break
		# Modal composition preserves the infobar underneath this overlay.
		# Older images without wfModal still only cover the reserved row.
		if hasattr(eWindow, "wfModal"):
			screen.instance.setFlag(eWindow.wfModal)
		screen.setAnimationMode(0)
		screen.instance.resize(eSize(width, round(32 * factor)))
		screen.instance.move(ePoint(0, top))


def history_labels(screen):
    """Keep EPG line breaks out of the single-line History Zap text fields."""
    source = screen['menu']
    rows = []
    changed = False
    for entry in source.list:
        row = list(entry)
        for index in (2, 3, 4):
            if index < len(row) and isinstance(row[index], str):
                text = ' '.join(row[index].replace('\x8a', ' ').replace('\ue08a', ' ').split())
                changed |= text != row[index]
                row[index] = text
        # Native History Zap uses an empty string for missing picons; MultiContent expects None.
        if len(row) > 6 and row[6] == '':
            row[6] = None
            changed = True
        rows.append(tuple(row) if isinstance(entry, tuple) else row)
    if changed:
        source.updateList(rows)


def config_split(screen):
    screen['config'].l.setSeperation(screen['config'].instance.size().width() // 2)


def choice_layout(screen):
    from enigma import eLabel, ePoint, eSize, getDesktop

    desktop = getDesktop(0).size()
    factor = desktop.width() / 1280.0
    params = getattr(screen, 'params', None) or {}

    def bounded(key, fallback, minimum, maximum):
        try:
            value = int(float(params.get(key, fallback)) * factor)
        except (TypeError, ValueError, OverflowError):
            value = int(fallback * factor)
        return max(int(minimum * factor), min(maximum, value))

    width = bounded('width', 760, 420, desktop.width() - int(48 * factor))
    height = bounded('height', 500, 192, desktop.height() - int(48 * factor))
    screen.instance.resize(eSize(width, height))
    screen.instance.move(ePoint((desktop.width() - width) // 2, (desktop.height() - height) // 2))
    listing = screen['list'].instance
    listing.move(ePoint(int(16 * factor), int(78 * factor)))
    listing.resize(eSize(width - int(32 * factor), height - int(102 * factor)))
    for widget in getattr(screen, 'additionalWidgets', ()):
        instance = widget.instance
        if isinstance(instance, eLabel) and instance.position().x() == instance.position().y() == 0:
            instance.resize(eSize(width, height))
    for renderer in getattr(screen, 'renderer', ()):
        if isinstance(renderer.instance, eLabel) and renderer.instance.position().y() < int(60 * factor):
            renderer.instance.resize(eSize(width - int(48 * factor), int(40 * factor)))
