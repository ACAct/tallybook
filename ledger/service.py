"""记账服务门面：组装各业务模块，对外保持 Ledger 接口不变。

本文件只做组装，不含业务逻辑；各能力由以下成员各自的文件维护：
B1 record_add.py、B2 record_edit.py、B3 query.py、
C1 summary.py、C2 importer.py、C3 exporter.py。
"""
from .exporter import LedgerExporter
from .importer import LedgerImporter
from .query import LedgerQuery
from .record_add import LedgerAdd
from .record_edit import LedgerEdit
from .storage import JsonStore
from .summary import LedgerSummary


class Ledger(LedgerAdd, LedgerEdit, LedgerQuery, LedgerSummary, LedgerImporter, LedgerExporter):
    """组合各业务混入类；对外接口与旧版 Ledger 完全一致。"""

    def __init__(self, path):
        self.store = JsonStore(path)
