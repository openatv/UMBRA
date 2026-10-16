from enigma import gRGB

from Components.Renderer.Label import Label


class UmbraRatingLabel(Label):
	WHITE = 0x00FFFFFF

	def applySkin(self, desktop, parent):
		result = Label.applySkin(self, desktop, parent)
		self.changed((self.CHANGED_DEFAULT,))
		return result

	def formatRating(self, value):
		text, separator, colorText = (value or "").partition(";")
		text = text.strip()
		color = self.WHITE
		if text in ("All ages", _("All ages"), "0"):
			text = "0"
		elif text:
			if text.isdecimal():
				text = f"{text}+"
			if separator and colorText.startswith("#"):
				try:
					color = int(colorText[1:], 16) & 0x00FFFFFF
				except ValueError:
					color = self.WHITE
		return text, color

	def changed(self, what):
		value = self.source.text if what[0] != self.CHANGED_CLEAR and self.source else ""
		text, color = self.formatRating(value)
		self.text = text
		if self.instance:
			self.instance.setForegroundColor(gRGB(color))
			self.instance.setWidgetBorderColor(gRGB(color))
			if text:
				self.instance.show()
			else:
				self.instance.hide()
