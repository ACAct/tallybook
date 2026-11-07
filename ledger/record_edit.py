"""B2 · 记录修改与删除。

本文件只由 B2 成员维护：按 id 更新/删除，保留 id 与创建时间。
"""
from .schema import validate_entry


class LedgerEdit:
    def update(self, rid, data):
        with self.store.transaction():
            records = self.store.read()
            for index, old in enumerate(records):
                if old["id"] == rid:
                    records[index] = validate_entry(data, old)
                    self.store.write(records)
                    return records[index]
            raise KeyError("记录不存在，可能已被删除")

    def delete(self, rid):
        with self.store.transaction():
            records = self.store.read()
            remaining = [row for row in records if row["id"] != rid]
            if len(remaining) == len(records):
                raise KeyError("记录不存在，可能已被删除")
            self.store.write(remaining)
