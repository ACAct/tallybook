"""B1 · 记录新增。

本文件只由 B1 成员维护：校验输入、写入账本、返回带唯一 id 的新记录。
"""
from .schema import MAX_RECORDS, validate_entry


class LedgerAdd:
    def add(self, data):
        record = validate_entry(data)
        with self.store.transaction():
            records = self.store.read()
            if len(records) >= MAX_RECORDS:
                raise ValueError("账本最多支持 20,000 笔记录")
            records.append(record)
            self.store.write(records)
        return record
