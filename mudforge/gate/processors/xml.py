from xml.etree import ElementTree
from rich.text import Text
from rich.style import Style
from mudforge.gate.conn import StyleOptions
from mudforge.utils import import_from_module

from .base import BaseProcessor


def render_xml_text(processor, element) -> Text:
    """
    Renders a <text> element and its <span> contents into a single Text object.
    """
    style = processor.extract_style(element)
    t = Text(element.text, style=style)
    for i in range(len(element)):
        e = element[i]
        t.append(Text(e.text, style=processor.extract_style(e)))
        if e.tail:
            t.append(e.tail)
    if element.tail:
        t.append(element.tail)
    return t


class XmlProcessor(BaseProcessor):

    def __init__(self, app):
        super().__init__(app)
        self.funcs = dict()

    def setup(self):
        for name, path in self.app.config.get("xml_functions", dict()).items():
            self.funcs[name] = import_from_module(path)

    def extract_style(self, element):
        if not element.attrib:
            return None
        kwargs = dict()
        attribs = element.attrib.copy()
        options = int(attribs.pop("options")) if "options" in attribs else 0
        no_options = int(attribs.pop("no_options")) if "no_options" in attribs else 0
        s = StyleOptions

        for c in ("color", "bgcolor", "link", "tag"):
            if c in attribs:
                if attribs[c].lower() in ("none", "null"):
                    kwargs[c] = None
                else:
                    kwargs[c] = attribs[c]

        if options or no_options:
            for code, kw in ((s.BOLD, "bold"), (s.DIM, "dim"), (s.ITALIC, "italic"), (s.UNDERLINE, "underline"),
                             (s.BLINK, "blink"), (s.BLINK2, "blink"), (s.REVERSE, "reverse"), (s.CONCEAL, "conceal"),
                             (s.STRIKE, "strike"), (s.UNDERLINE2, "underline2"), (s.FRAME, "frame"),
                             (s.ENCIRCLE, "encircle"),
                             (s.OVERLINE, "overline")):
                if code & options:
                    kwargs[kw] = True
                if code & no_options:
                    kwargs[kw] = False

        kwargs["xml_attr"] = attribs
        return Style(**kwargs)

    def print_xml(self, entry):
        tree = ElementTree.fromstring(entry)
        tag = tree.tag.lower()
        if tag in self.funcs:
            return self.funcs[tag](self, tree)

    async def process(self, conn, body):
        for entry in body:
            rendered = self.print_xml(entry["data"])
            if rendered is None:
                continue
            mode = entry.get("mode", "line").lower()
            match mode:
                case ("line" | "prompt" | "text"):
                    await conn.send_text_data(mode, conn.print(rendered))
                case _:
                    pass