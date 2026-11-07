"""C3 · 导出（JSON 完整备份 / CSV 筛选记录）。

本文件只由 C3 成员维护：JSON 忽略筛选导出全量，CSV 应用筛选并做转义与公式防护。
"""
import csv
import io


class LedgerExporter:
    def export_json(self):
        return {"version": 1, "records": self.store.read()}

    def export_csv(self, filters):
        def safe(value):
            # 防止备注在电子表格中被解释为公式。
            return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(["日期", "类型", "金额（元）", "类别", "备注"])
        for row in self.query(filters):
            amount = row["amount_cents"]
            writer.writerow([row["date"], "收入" if row["type"] == "income" else "支出",
                             f"{amount // 100}.{amount % 100:02d}", safe(row["category"]), safe(row["note"])])
        return "\ufeff" + output.getvalue()
