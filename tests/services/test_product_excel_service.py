from io import BytesIO
from pathlib import Path
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


def test_parse_reads_legacy_xls_sheets() -> None:
    class FakeSheet(object):
        name = "Add Product"
        nrows = 2

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

    with patch(
        "src.services.product_excel_service.xlrd.open_workbook",
        return_value=FakeWorkbook(),
    ):
        rows = ProductExcelService.parse("products.xls", b"xls-bytes")

    assert rows[0].name == "Legacy"
    assert rows[0].stock == 2


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
