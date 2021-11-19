from xml.etree import ElementTree
from rich.text import Text
from rich.style import Style
from mudforge.gate.conn import StyleOptions

XML_RENDER_FUNCS = dict()


def extract_style(element):
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


def print_xml(entry):
    tree = ElementTree.fromstring(entry)
    if tree.tag.lower() == "text":
        return render_xml_text(tree)


def render_xml_text(element):
    """
    Renders a <text> element and its <span> contents into a single Text object.
    """
    style = extract_style(element)
    t = Text(element.text, style=style)
    for i in range(len(element)):
        e = element[i]
        t.append(Text(e.text, style=extract_style(e)))
        if e.tail:
            t.append(e.tail)
    if element.tail:
        t.append(element.tail)
    return t


async def process_xml(conn, body):
    for entry in body:
        rendered = print_xml(entry["data"])
        mode = entry.get("mode", "line").lower()
        match mode:
            case ("line" | "prompt" | "text"):
                await conn.send_text_data(mode, conn.print(rendered))
            case _:
                pass
