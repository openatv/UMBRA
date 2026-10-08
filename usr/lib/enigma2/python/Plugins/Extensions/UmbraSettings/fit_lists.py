"""Fit Umbra list viewports to complete native rows, without changing content."""

from enigma import eListbox, eSize, eTimer


def fitted_height(limit, item_height):
    if item_height <= 0 or limit < item_height:
        return limit
    return limit // item_height * item_height


# The native selectionChanged emitter iterates its callback list by index without
# holding references, so it must never be modified while a signal is running.
_detached = []


def _flushDetached():
    while _detached:
        callbacks, callback = _detached.pop()
        if callback in callbacks:
            callbacks.remove(callback)


_detachTimer = eTimer()
_detachTimer.callback.append(_flushDetached)


def _detach(callbacks, callback):
    _detached.append((callbacks, callback))
    _detachTimer.start(0, True)


class ListFitter:
    def __init__(self, screen):
        self.screen = screen
        self.bindings = []
        self.timer = eTimer()
        self.timer.callback.append(self.apply)
        seen = set()
        for component in list(screen.values()) + screen.renderer:
            instance = getattr(component, "instance", None)
            if not isinstance(instance, eListbox) or id(instance) in seen:
                continue
            seen.add(id(instance))
            callbacks = instance.selectionChanged.get()
            # Holding the eListbox would keep it alive (and focused) after GUIComponent.destroy().
            self.bindings.append((component, instance.size().width(), instance.size().height(), callbacks))
            callbacks.append(self.fit)
        screen.onShown.append(self.fit)
        screen.onClose.append(self.close)
        self.apply()

    def fit(self):
        # Resizing re-enters eListbox::moveSelection(), so leave the signal first.
        if self.bindings:
            self.timer.start(0, True)

    def apply(self):
        for binding in self.bindings[:]:
            component, width, limit, callbacks = binding
            # GUIComponent.destroy() clears the renderer's entire __dict__.
            instance = getattr(component, "instance", None)
            if not isinstance(instance, eListbox):
                _detach(callbacks, self.fit)
                self.bindings.remove(binding)
                continue
            height = fitted_height(limit, instance.getItemHeight())
            if instance.getOrientation() == eListbox.orHorizontal:
                height = limit
            if instance.size().height() != height:
                instance.resize(eSize(width, height))

    def close(self):
        self.timer.stop()
        for _, _, _, callbacks in self.bindings:
            _detach(callbacks, self.fit)
        self.bindings.clear()
        if self.fit in self.screen.onShown:
            self.screen.onShown.remove(self.fit)


def install(screen):
    previous = getattr(screen, "_umbraListFitter", None)
    if previous:
        previous.close()
        if previous.close in screen.onClose:
            screen.onClose.remove(previous.close)
    screen._umbraListFitter = ListFitter(screen)
