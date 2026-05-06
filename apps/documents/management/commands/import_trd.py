import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.documents.models import Dependencia, SerieDocumental, SubserieDocumental, TipoDocumental


class Command(BaseCommand):
    help = "Importa tablas de retencion documental desde un archivo .xlsx organizado por hojas."

    SPREADSHEET_NS = {
        "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
    }

    def add_arguments(self, parser):
        parser.add_argument("xlsx_path", type=str, help="Ruta del archivo .xlsx con la TRD.")

    def handle(self, *args, **options):
        xlsx_path = Path(options["xlsx_path"]).expanduser()
        if not xlsx_path.exists():
            raise CommandError(f"No existe el archivo: {xlsx_path}")
        if xlsx_path.suffix.lower() != ".xlsx":
            raise CommandError("El archivo debe tener extension .xlsx")

        workbook = self._load_workbook(xlsx_path)
        stats = {"dependencias": 0, "series": 0, "subseries": 0, "tipos": 0}

        with transaction.atomic():
            for sheet_name, rows in workbook:
                imported = self._import_sheet(sheet_name, rows)
                for key, value in imported.items():
                    stats[key] += value

        self.stdout.write(self.style.SUCCESS("Importacion completada."))
        self.stdout.write(
            f"Dependencias: {stats['dependencias']} | Series: {stats['series']} | "
            f"Subseries: {stats['subseries']} | Tipos: {stats['tipos']}"
        )

    def _load_workbook(self, xlsx_path):
        with zipfile.ZipFile(xlsx_path) as archive:
            shared_strings = self._shared_strings(archive)
            workbook_xml = ET.fromstring(archive.read("xl/workbook.xml"))
            rels_xml = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            rels_map = {
                rel.attrib["Id"]: rel.attrib["Target"]
                for rel in rels_xml.findall("pr:Relationship", self.SPREADSHEET_NS)
            }

            workbook = []
            for sheet in workbook_xml.find("a:sheets", self.SPREADSHEET_NS):
                name = sheet.attrib.get("name", "").strip()
                rel_id = sheet.attrib.get(
                    "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
                )
                target = rels_map.get(rel_id)
                if not target:
                    continue
                sheet_path = target if target.startswith("xl/") else f"xl/{target}"
                rows = self._parse_sheet(archive, sheet_path, shared_strings)
                workbook.append((name, rows))
            return workbook

    def _shared_strings(self, archive):
        if "xl/sharedStrings.xml" not in archive.namelist():
            return []

        sst = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        values = []
        for item in sst.findall("a:si", self.SPREADSHEET_NS):
            text = "".join(node.text or "" for node in item.iterfind(".//a:t", self.SPREADSHEET_NS))
            values.append(text)
        return values

    def _parse_sheet(self, archive, sheet_path, shared_strings):
        root = ET.fromstring(archive.read(sheet_path))
        rows = []
        for row in root.findall(".//a:sheetData/a:row", self.SPREADSHEET_NS):
            parsed = {}
            for cell in row.findall("a:c", self.SPREADSHEET_NS):
                ref = cell.attrib.get("r", "")
                match = re.match(r"([A-Z]+)", ref)
                if not match:
                    continue
                column = match.group(1)
                value = self._cell_value(cell, shared_strings)
                parsed[column] = value.strip() if isinstance(value, str) else value
            rows.append(parsed)
        return rows

    def _cell_value(self, cell, shared_strings):
        cell_type = cell.attrib.get("t")
        value = cell.find("a:v", self.SPREADSHEET_NS)
        if value is not None:
            raw = value.text or ""
            if cell_type == "s" and raw.isdigit():
                index = int(raw)
                return shared_strings[index] if index < len(shared_strings) else raw
            return raw

        inline_string = cell.find("a:is", self.SPREADSHEET_NS)
        if inline_string is not None:
            return "".join(node.text or "" for node in inline_string.iterfind(".//a:t", self.SPREADSHEET_NS))
        return ""

    def _import_sheet(self, sheet_name, rows):
        oficina = self._extract_office_name(sheet_name, rows)
        dep_code, dep_name = self._split_code_name(oficina or sheet_name)
        if not dep_code:
            raise CommandError(f"No pude identificar el codigo de dependencia en la hoja: {sheet_name}")

        dependencia, dep_created = Dependencia.objects.update_or_create(
            code=dep_code,
            defaults={"name": dep_name or sheet_name, "is_active": True},
        )

        current_serie = None
        current_subserie = None
        stats = {
            "dependencias": 1 if dep_created else 0,
            "series": 0,
            "subseries": 0,
            "tipos": 0,
        }

        for row in rows:
            description = row.get("D", "").strip()
            if not description:
                continue

            serie_code = row.get("B", "").strip()
            subserie_code = row.get("C", "").strip()
            dep_cell = row.get("A", "").strip()

            if description.startswith("-"):
                if current_subserie is None:
                    continue
                tipo_name = description.lstrip("-").strip()
                _, created = TipoDocumental.objects.update_or_create(
                    subserie=current_subserie,
                    name=tipo_name,
                    defaults={"is_active": True},
                )
                if created:
                    stats["tipos"] += 1
                continue

            if serie_code and not subserie_code and dep_cell and self._is_code(dep_cell):
                current_serie, created = SerieDocumental.objects.update_or_create(
                    dependencia=dependencia,
                    code=serie_code,
                    defaults={"name": description, "is_active": True},
                )
                current_subserie = None
                if created:
                    stats["series"] += 1
                continue

            if serie_code and subserie_code and current_serie and self._is_code(dep_cell):
                current_subserie, created = SubserieDocumental.objects.update_or_create(
                    serie=current_serie,
                    code=subserie_code,
                    defaults={
                        "name": description,
                        "retention_management": self._to_int(row.get("E")),
                        "retention_central": self._to_int(row.get("F")),
                        "disposition_ct": row.get("G", "").strip().upper() == "CT",
                        "disposition_e": row.get("H", "").strip().upper() == "E",
                        "disposition_d": row.get("I", "").strip().upper() == "D",
                        "disposition_s": row.get("J", "").strip().upper() == "S",
                        "procedures": row.get("K", "").strip(),
                        "is_active": True,
                    },
                )
                if created:
                    stats["subseries"] += 1

        return stats

    def _extract_office_name(self, sheet_name, rows):
        for row in rows:
            office_text = row.get("A", "")
            if office_text.startswith("OFICINA PRODUCTORA:"):
                return office_text.split(":", 1)[1].strip()
        return sheet_name

    def _split_code_name(self, value):
        cleaned = " ".join(value.split())
        match = re.match(r"^([0-9]+(?:-[0-9]+)?)\s+(.*)$", cleaned)
        if not match:
            return "", cleaned
        return match.group(1), match.group(2).strip()

    def _is_code(self, value):
        return bool(re.match(r"^[0-9]+(?:-[0-9]+)?$", value))

    def _to_int(self, value):
        text = str(value or "").strip()
        if not text:
            return 0
        try:
            return int(float(text))
        except ValueError:
            return 0
