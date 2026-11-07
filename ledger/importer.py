"""C2 · JSON 导入与合并。

本文件只由 C2 成员维护：整文件先校验，去重合并，冲突/非法整批取消。
"""
from .schema import MAX_RECORDS, validate_document


class LedgerImporter:
    def import_json(self, document):
        incoming = validate_document(document)
        with self.store.transaction():
            records = self.store.read()
            by_id = {row["id"]: row for row in records}
            added = skipped = 0
            for row in incoming:
                if row["id"] in by_id:
                    if row != by_id[row["id"]]:
                        raise ValueError("备份中有相同编号的不同记录，导入已取消；请先核对备份版本")
                    skipped += 1
                else:
                    records.append(row)
                    added += 1
            if len(records) > MAX_RECORDS:
                raise ValueError("导入后超过 20,000 笔记录上限")
            if added:
                self.store.write(records)
            return {"added": added, "skipped": skipped}
