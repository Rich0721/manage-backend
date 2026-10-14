from io import BytesIO
from pathlib import Path
import struct
from unittest.mock import patch

from openpyxl import Workbook, load_workbook
import pytest

from src.services.product_excel_service import ProductExcelError
from src.services.product_excel_service import ProductExcelService


def make_workbook_bytes() -> bytes:
    workbook = Workbook()
    add_sheet = workbook.active
    add_sheet.title = "Add Product"
    add_sheet.append(["商品名稱", "商品分類", "成本", "價格", "庫存"])
    add_sheet.append(["New", "Label A", 10, 20, None])
    update_sheet = workbook.create_sheet("Update Product")
    update_sheet.append(
        ["商品ID", "商品名稱", "商品分類", "成本", "價錢", "庫存"]
    )
    update_sheet.append(
        ["1790705105001", "Existing", "Label B", 30, 40, 5]
    )
    workbook.create_sheet("Ignored")
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def test_parse_xlsx_sheets_and_price_alias() -> None:
    rows = ProductExcelService.parse("products.xlsx", make_workbook_bytes())

    assert len(rows) == 2
    assert rows[0].operation == "add"
    assert rows[0].stock == 0
    assert rows[0].price == 20
    assert rows[1].operation == "update"
    assert rows[1].product_id == "1790705105001"


def test_parse_rejects_missing_add_headers() -> None:
    workbook = Workbook()
    workbook.active.title = "Add Product"
    workbook.active.append(["商品名稱"])
    output = BytesIO()
    workbook.save(output)

    with pytest.raises(ProductExcelError) as error:
        ProductExcelService.parse("products.xlsx", output.getvalue())

    assert error.value.public_message == ProductExcelService.ADD_HEADERS_ERROR


def test_parse_rejects_invalid_update_rows() -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Update Product"
    sheet.append(["商品ID", "商品名稱", "商品分類", "成本", "價錢", "庫存"])
    sheet.append(["1790705105001", "Bad", "Label", 10, 20, -1])
    output = BytesIO()
    workbook.save(output)

    with pytest.raises(ProductExcelError) as error:
        ProductExcelService.parse("products.xlsx", output.getvalue())

    assert error.value.public_message == ProductExcelService.UPDATE_DATA_ERROR


@pytest.mark.parametrize("invalid_value", ["=1+1", "#VALUE!"])
def test_parse_rejects_formula_and_error_cells(invalid_value: str) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Add Product"
    sheet.append(["商品名稱", "商品分類", "成本", "價錢", "庫存"])
    sheet.append([invalid_value, "Label", 10, 20, 0])
    if invalid_value.startswith("#"):
        sheet["A2"].data_type = "e"
    output = BytesIO()
    workbook.save(output)

    with pytest.raises(ProductExcelError) as error:
        ProductExcelService.parse("products.xlsx", output.getvalue())

    assert error.value.public_message == ProductExcelService.ADD_DATA_ERROR


def test_parse_reads_legacy_xls_sheets() -> None:
    class FakeSheet(object):
        name = "Add Product"
        nrows = 2

        class Cell(object):
            def __init__(self, value: object) -> None:
                self.value = value
                self.ctype = 1

        @classmethod
        def row(cls, row_index: int) -> list[object]:
            return [cls.Cell(value) for value in cls.row_values(row_index)]

        @staticmethod
        def row_values(row_index: int) -> list[object]:
            if row_index == 0:
                return ["商品名稱", "商品分類", "成本", "價錢", "庫存"]
            return ["Legacy", "Label", 10, 20, 2]

    class FakeWorkbook(object):
        @staticmethod
        def sheets() -> list[FakeSheet]:
            return [FakeSheet()]

        @staticmethod
        def release_resources() -> None:
            return None

    class FakeCompoundDocument(object):
        @staticmethod
        def get_named_stream(name: str) -> bytes:
            return b""

    with (
        patch(
            "src.services.product_excel_service.xlrd.open_workbook",
            return_value=FakeWorkbook(),
        ),
        patch(
            "src.services.product_excel_service.xlrd.compdoc.CompDoc",
            return_value=FakeCompoundDocument(),
        ),
    ):
        rows = ProductExcelService.parse("products.xls", b"xls-bytes")

    assert rows[0].name == "Legacy"
    assert rows[0].stock == 2


def test_parse_rejects_formula_in_legacy_xls() -> None:
    class FakeCell(object):
        def __init__(self, value: object) -> None:
            self.value = value
            self.ctype = 1

    class FakeSheet(object):
        name = "Add Product"
        nrows = 2

        @staticmethod
        def row(row_index: int) -> list[FakeCell]:
            values = (
                ["商品名稱", "商品分類", "成本", "價錢", "庫存"]
                if row_index == 0
                else ["Calculated formula", "Label", 10, 20, 0]
            )
            return [FakeCell(value) for value in values]

    class FakeWorkbook(object):
        @staticmethod
        def sheets() -> list[FakeSheet]:
            return [FakeSheet()]

        @staticmethod
        def release_resources() -> None:
            return None

    def record(record_id: int, data: bytes) -> bytes:
        return struct.pack("<HH", record_id, len(data)) + data

    name = b"Add Product"
    boundsheet = record(0x0085, b"\0\0\0\0\0\0" + bytes([len(name), 0]) + name)
    sheet_offset = len(boundsheet)
    boundsheet_data = (
        struct.pack("<I", sheet_offset)
        + b"\0\0"
        + bytes([len(name), 0])
        + name
    )
    formula_stream = (
        record(0x0085, boundsheet_data)
        + record(0x0809, b"")
        + record(0x0006, struct.pack("<HH", 1, 0) + bytes(20))
        + record(0x000A, b"")
    )

    class FakeCompoundDocument(object):
        def __init__(self, content: bytes, logfile: object) -> None:
            return None

        @staticmethod
        def get_named_stream(name: str) -> bytes:
            return formula_stream

    with (
        patch(
            "src.services.product_excel_service.xlrd.open_workbook",
            return_value=FakeWorkbook(),
        ),
        patch(
            "src.services.product_excel_service.xlrd.compdoc.CompDoc",
            FakeCompoundDocument,
        ),
        pytest.raises(ProductExcelError) as error,
    ):
        ProductExcelService.parse("products.xls", b"xls-bytes")

    assert error.value.public_message == ProductExcelService.ADD_DATA_ERROR


def test_parse_rejects_error_cell_in_legacy_xls() -> None:
    class FakeCell(object):
        def __init__(self, value: object, cell_type: int = 1) -> None:
            self.value = value
            self.ctype = cell_type

    class FakeSheet(object):
        name = "Add Product"
        nrows = 2

        @staticmethod
        def row(row_index: int) -> list[FakeCell]:
            values = (
                ["商品名稱", "商品分類", "成本", "價錢", "庫存"]
                if row_index == 0
                else ["Bad", "Label", "#VALUE!", 20, 0]
            )
            return [
                FakeCell(value, 5 if value == "#VALUE!" else 1)
                for value in values
            ]

    class FakeWorkbook(object):
        @staticmethod
        def sheets() -> list[FakeSheet]:
            return [FakeSheet()]

        @staticmethod
        def release_resources() -> None:
            return None

    class FakeCompoundDocument(object):
        @staticmethod
        def get_named_stream(name: str) -> bytes:
            return b""

    with (
        patch(
            "src.services.product_excel_service.xlrd.open_workbook",
            return_value=FakeWorkbook(),
        ),
        patch(
            "src.services.product_excel_service.xlrd.compdoc.CompDoc",
            return_value=FakeCompoundDocument(),
        ),
        pytest.raises(ProductExcelError) as error,
    ):
        ProductExcelService.parse("products.xls", b"xls-bytes")

    assert error.value.public_message == ProductExcelService.ADD_DATA_ERROR


def test_template_and_export_have_required_sheets_and_headers() -> None:
    template = load_workbook(BytesIO(ProductExcelService.create_template()))
    exported = load_workbook(
        BytesIO(ProductExcelService.create_workbook([]))
    )

    assert template.sheetnames == ["Add Product", "Update Product"]
    assert list(template["Add Product"].values)[0] == (
        "商品名稱",
        "商品分類",
        "成本",
        "價錢",
        "庫存",
    )
    assert exported.sheetnames == ["Update Product"]
    assert list(exported["Update Product"].values)[0] == (
        "商品ID",
        "商品名稱",
        "商品分類",
        "成本",
        "價錢",
        "庫存",
    )


def test_static_template_is_readable_and_contains_both_operations() -> None:
    template_path = Path("files/Batch Add Products.xlsx")
    workbook = load_workbook(template_path, read_only=True, data_only=True)

    assert workbook.sheetnames == ["Add Product", "Update Product"]
    assert next(workbook["Add Product"].values) == (
        "商品名稱",
        "商品分類",
        "成本",
        "價錢",
        "庫存",
    )
    assert next(workbook["Update Product"].values) == (
        "商品ID",
        "商品名稱",
        "商品分類",
        "成本",
        "價錢",
        "庫存",
    )
    workbook.close()
