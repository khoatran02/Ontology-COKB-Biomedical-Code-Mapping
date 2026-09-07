from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"m": MAIN_NS, "r": REL_NS, "p": PACKAGE_REL_NS}


def _column_index(reference: str) -> int:
    match = re.match(r"[A-Z]+", reference)
    if match is None:
        raise ValueError(f"Invalid cell reference: {reference}")
    index = 0
    for character in match.group():
        index = index * 26 + ord(character) - 64
    return index - 1


def read_first_sheet_records(path: str | Path) -> list[dict[str, str]]:
    """Read simple tabular XLSX data using only the Python standard library."""
    with ZipFile(path) as archive:
        names = set(archive.namelist())
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in names:
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall("m:si", NS):
                shared_strings.append(
                    "".join(node.text or "" for node in item.iterfind(".//m:t", NS))
                )

        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        relationships = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relationship_targets = {
            item.attrib["Id"]: item.attrib["Target"] for item in relationships
        }
        first_sheet = next(iter(workbook.find("m:sheets", NS)))
        relationship_id = first_sheet.attrib[f"{{{REL_NS}}}id"]
        target = relationship_targets[relationship_id]
        if target.startswith("/"):
            sheet_path = target.lstrip("/")
        elif target.startswith("xl/"):
            sheet_path = target
        else:
            sheet_path = str(Path("xl") / target)

        sheet = ElementTree.fromstring(archive.read(sheet_path))
        rows: list[list[str]] = []
        for row in sheet.iterfind(".//m:sheetData/m:row", NS):
            values: dict[int, str] = {}
            for cell in row.findall("m:c", NS):
                index = _column_index(cell.attrib["r"])
                cell_type = cell.attrib.get("t")
                value_element = cell.find("m:v", NS)
                if cell_type == "inlineStr":
                    value = "".join(
                        node.text or "" for node in cell.iterfind(".//m:t", NS)
                    )
                elif value_element is None:
                    value = ""
                elif cell_type == "s":
                    value = shared_strings[int(value_element.text)]
                elif cell_type == "b":
                    value = "TRUE" if value_element.text == "1" else "FALSE"
                else:
                    value = value_element.text or ""
                values[index] = value
            if not values:
                continue
            materialized = [""] * (max(values) + 1)
            for index, value in values.items():
                materialized[index] = value
            rows.append(materialized)

    if not rows:
        return []
    headers = rows[0]
    return [
        {
            header: row[index] if index < len(row) else ""
            for index, header in enumerate(headers)
            if header
        }
        for row in rows[1:]
    ]
