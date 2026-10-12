from glob import glob
from math import isfinite
from os.path import dirname, join

from enigma import eTimer


class SystemMetrics:
	def __init__(self):
		self.previousCpu = None

	@staticmethod
	def readText(path):
		try:
			with open(path, encoding="ascii", errors="replace") as source:
				return source.read()
		except OSError:
			return ""

	def cpuUsage(self):
		try:
			fields = self.readText("/proc/stat").splitlines()[0].split()
			if fields[0] != "cpu" or len(fields) < 5:
				raise ValueError("Missing CPU counters")
			# Guest counters are already included in user/nice; iowait is idle time.
			values = [int(x) for x in fields[1:9]]
			if any(x < 0 for x in values):
				raise ValueError("Invalid CPU counters")
			current = (sum(values), values[3] + (values[4] if len(values) > 4 else 0))
		except (ValueError, IndexError):
			self.previousCpu = None
			return None
		previous, self.previousCpu = self.previousCpu, current
		if previous is None:
			return None
		total, idle = current[0] - previous[0], current[1] - previous[1]
		return round(100 * (total - idle) / total) if total > 0 and 0 <= idle <= total else None

	def ramUsage(self):
		try:
			values = {x.split(":", 1)[0]: int(x.split()[1]) for x in self.readText("/proc/meminfo").splitlines() if ":" in x}
			total = values["MemTotal"]
			available = values.get("MemAvailable")
			if available is None:
				available = values["MemFree"] + sum(values.get(x, 0) for x in ("Buffers", "Cached", "SReclaimable")) - values.get("Shmem", 0)
			return round(100 * (total - min(total, max(0, available))) / total) if total > 0 else None
		except (ValueError, KeyError, IndexError):
			return None

	def temperature(self):
		paths = ["/proc/stb/fp/temp_sensor_avs", "/proc/stb/power/avs", "/proc/stb/sensors/temp0/value"]
		for path in sorted(glob("/sys/class/thermal/thermal_zone*/temp")):
			kind = self.readText(join(dirname(path), "type")).strip().lower()
			if any(x in kind for x in ("cpu", "soc", "avs")):
				paths.append(path)
		for path in paths:
			try:
				value = float(self.readText(path).strip())
				if path.startswith("/sys/") or abs(value) >= 1000:
					value /= 1000
				if isfinite(value) and -20 <= value <= 150:
					return round(value)
			except ValueError:
				pass
		return None


class SystemInfoController:
	PLACEHOLDER = "CPU --   RAM --"

	def __init__(self, parent, label):
		self.parent = parent
		self.label = label
		self.closed = False
		self.visible = False
		self.metrics = SystemMetrics()
		self.timer = eTimer()
		self.timer.callback.append(self.update)
		self.hooks = ((parent.onShown, self.show), (parent.onShow, self.show), (parent.onHide, self.hide), (parent.onExecEnd, self.hide), (parent.onClose, self.close))
		for callbacks, method in self.hooks:
			callbacks.append(method)

	def show(self):
		if self.closed:
			return
		if not self.parent.shown or not self.parent.execing:
			self.hide()
		elif not self.visible:
			self.visible = True
			self.metrics.previousCpu = None
			self.update()

	def update(self):
		if self.closed or not self.visible:
			return
		parts = []
		for title, value in (("CPU", self.metrics.cpuUsage()), ("RAM", self.metrics.ramUsage())):
			parts.append(f"{title} {value}%" if value is not None else f"{title} --")
		temperature = self.metrics.temperature()
		if temperature is not None:
			parts.append(f"{temperature} \u00b0C")
		self.label.setText("   ".join(parts))
		self.timer.start(2000, True)

	def hide(self):
		self.visible = False
		self.timer.stop()

	def close(self):
		if self.closed:
			return
		self.closed = True
		self.hide()
		for callbacks, method in self.hooks:
			if method in callbacks:
				callbacks.remove(method)
		self.timer.callback.remove(self.update)
		self.label = None


def install(parent, enabled=False):
	previous = getattr(parent, "umbraSystemInfo", None)
	if previous is not None:
		previous.close()
	parent.umbraSystemInfo = None
	if enabled:
		# Native eLabel names are not retained; bind the skin-owned label by its initial text.
		for widget in parent.additionalWidgets:
			if ("text", SystemInfoController.PLACEHOLDER) in widget.skinAttributes:
				parent.umbraSystemInfo = SystemInfoController(parent, widget.instance)
				parent.umbraSystemInfo.show()
				break
