"""Fit Umbra list viewports to complete native rows, without changing content."""

from enigma import eListbox, eSize


def fitted_height(limit, item_height):
    if item_height <= 0 or limit < item_height:
        return limit
    return limit // item_height * item_height


class ListFitter:
    def __init__(self, screen):
        self.screen = screen
        self.bindings = []
        self.busy = False
        seen = set()
        for component in list(screen.values()) + screen.renderer:
            instance = getattr(component, "instance", None)
            if not isinstance(instance, eListbox) or id(instance) in seen:
                continue
            seen.add(id(instance))
            callbacks = instance.selectionChanged.get()
            self.bindings.append((component, instance, instance.size().width(), instance.size().height(), callbacks))
            callbacks.append(self.fit)
        screen.onShown.append(self.fit)
        screen.onClose.append(self.close)
        self.fit()

    def fit(self):
        if self.busy:
            return
        self.busy = True
        try:
            for component, instance, width, limit, _ in self.bindings:
                if component.instance is not instance:
                    continue
                height = fitted_height(limit, instance.getItemHeight())
                if instance.getOrientation() == eListbox.orHorizontal:
                    height = limit
                if instance.size().height() != height:
                    instance.resize(eSize(width, height))
        finally:
            self.busy = False

    def close(self):
        for _, _, _, _, callbacks in self.bindings:
            if self.fit in callbacks:
                callbacks.remove(self.fit)
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
