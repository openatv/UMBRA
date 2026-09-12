"""Factor identical screen fragments into native panels, without changing widgets."""

from collections import defaultdict
from copy import deepcopy
import hashlib
import xml.etree.ElementTree as ET


def signature(element):
    return (element.tag, tuple(sorted(element.items())), (element.text or "").strip(),
            tuple(signature(child) for child in element))


def xml_size(root):
    root = deepcopy(root)
    ET.indent(root)
    return len(ET.tostring(root, encoding="utf-8"))


def compact_screens(root, prefix):
    """Only share literal adjacent widgets. Context-changing panels/applets stay put."""
    root = deepcopy(root)
    original_size = xml_size(root)
    originals = list(root.findall("screen"))
    generated = []
    safe = {"widget", "eLabel", "ePixmap", "eRectangle"}
    # Literal widgets do not change during factoring; avoid reserializing them per candidate.
    signatures = {id(child): signature(child) for screen in originals for child in screen if child.tag in safe}
    sizes = {id(child): len(ET.tostring(child, encoding="utf-8")) for screen in originals for child in screen if child.tag in safe}
    while True:
        candidates = defaultdict(list)
        for screen in originals:
            children = list(screen)
            for start, child in enumerate(children):
                if child.tag not in safe:
                    continue
                block = []
                for end in range(start, len(children)):
                    if children[end].tag not in safe:
                        break
                    block.append(signatures[id(children[end])])
                    candidates[tuple(block)].append((screen, start, end + 1))
        best, best_saving = None, 64
        for key, occurrences in candidates.items():
            # Share between screens, not repeating components inside the same screen.
            if len({id(s) for s, _, _ in occurrences}) != len(occurrences) or len(occurrences) < 2:
                continue
            s, start, end = occurrences[0]
            block_size = sum(sizes[id(x)] for x in list(s)[start:end])
            saving = (len(occurrences) - 1) * block_size - len(occurrences) * 65 - 80
            if saving > best_saving:
                best, best_saving = (key, occurrences), saving
        if best is None:
            break
        key, occurrences = best
        name = prefix + hashlib.sha256(repr(key).encode()).hexdigest()[:10]
        panel = ET.Element("screen", name=name)
        s, start, end = occurrences[0]
        panel.extend(deepcopy(list(s)[start:end]))
        generated.append(panel)
        for s, start, end in occurrences:
            for child in list(s)[start:end]:
                s.remove(child)
            s.insert(start, ET.Element("panel", name=name))
    root[:0] = generated
    return root, {"bytes_before": original_size, "bytes_after": xml_size(root),
                  "shared_blocks": len(generated),
                  "panel_references": sum(1 for _ in root.iter("panel"))}


def expand_screen(screen, screens, stack=()):
    """Expand only plain named references; preserve all conditions and converters."""
    result = deepcopy(screen)
    result[:] = []
    for element in screen:
        if element.tag == "panel" and set(element.attrib) == {"name"} and not len(element):
            name = element.get("name")
            if name in stack:
                raise ValueError("Recursive panel: " + name)
            if name not in screens:
                raise ValueError("Missing panel: " + name)
            result.extend(expand_screen(screens[name], screens, (*stack, name)))
        else:
            result.append(deepcopy(element))
    return result
