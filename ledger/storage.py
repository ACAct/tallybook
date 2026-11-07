"""A3 · JSON 持久化：原子写入 + 跨进程事务锁。

本文件只由 A3 成员维护。对外只承诺三件事：
1. read() 永远返回一份完整文档，文件不存在时是空账本，损坏时报错但绝不清空；
2. transaction() 里的「读 → 改 → 写」不会被别的线程或别的进程插进来；
3. write() 要么把新账本整体换上去，要么原账本一个字节都不动。
"""
import json
import os
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from .schema import validate_document

LOCK_TIMEOUT = 10.0   # 等锁文件、等文件锁的总时限（秒）
LOCK_INTERVAL = 0.05  # 轮询间隔（秒）
BROKEN = "账本无法读取或已损坏。原文件已保留，请检查数据文件或从备份恢复。"


class StorageError(Exception):
    """账本无法读写。抛出它时，磁盘上的原文件一定没有被改动。"""


class JsonStore:
    """同一数据路径在本进程内共用一把可重入锁；跨进程靠锁文件上的一把记录锁。"""

    _thread_locks = {}
    _registry = threading.Lock()

    def __init__(self, path):
        self.path = Path(path).resolve()
        self.lock_path = Path(str(self.path) + ".lock")
        key = str(self.path)
        with self._registry:
            # 多个 JsonStore 指向同一文件时必须拿到同一把线程锁，否则进程内也会互相覆盖。
            self.lock = self._thread_locks.setdefault(key, threading.RLock())

    # ---------- 读 ----------
    def read(self):
        with self.lock:
            if not self.path.exists():
                return []
            try:
                raw = self.path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                # 目录冒充数据文件、权限不足、编码损坏都走这里；原文件原样保留。
                raise StorageError(BROKEN) from exc
            try:
                return validate_document(json.loads(raw))
            except ValueError as exc:
                raise StorageError(BROKEN) from exc

    # ---------- 事务 ----------
    @contextmanager
    def transaction(self):
        """持锁期间完成「读 → 改 → 写」，避免多实例丢失更新。"""
        with self.lock:
            handle = self._open_lock_file()
            try:
                self._acquire(handle)
                try:
                    yield
                finally:
                    self._release(handle)
            finally:
                handle.close()

    # ---------- 写 ----------
    def write(self, records):
        with self.lock:
            tmp = None
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                # 先写同目录下的临时文件，落盘后再整体换名；两步之间原账本始终完好。
                fd, tmp = tempfile.mkstemp(prefix=".ledger-", suffix=".tmp", dir=str(self.path.parent))
                with os.fdopen(fd, "w", encoding="utf-8") as stream:
                    json.dump({"version": 1, "records": records}, stream, ensure_ascii=False, indent=2)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(tmp, str(self.path))
                tmp = None
                self._sync_directory()
            except (OSError, TypeError, ValueError) as exc:
                raise StorageError("保存失败，请检查磁盘空间和文件权限；原账本未被替换。") from exc
            finally:
                if tmp:
                    try:
                        os.unlink(tmp)
                    except OSError:
                        pass

    # ---------- 内部：锁文件 ----------
    def _open_lock_file(self):
        """并发时 Windows 偶发拒绝打开刚建好的锁文件（共享冲突、杀毒软件正在扫描）。

        这属于瞬时失败，重试即可；一次打不开就判定「目录不可写」会误报。
        """
        deadline = time.monotonic() + LOCK_TIMEOUT
        while True:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                return open(str(self.lock_path), "a+b")
            except OSError as exc:
                if time.monotonic() >= deadline:
                    raise StorageError("无法访问账本目录，请检查文件权限") from exc
                time.sleep(LOCK_INTERVAL)

    @staticmethod
    def _acquire(handle):
        if os.name == "nt":
            import msvcrt
            # 记录锁要求锁的字节范围真实存在，空文件先写一个占位字节。
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
            deadline = time.monotonic() + LOCK_TIMEOUT
            while True:
                handle.seek(0)
                try:
                    # 非阻塞加锁 + 自己轮询：比 LK_LOCK 的固定 1 秒粒度更可控，也便于给出中文提示。
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    return
                except OSError as exc:
                    if time.monotonic() >= deadline:
                        raise StorageError("账本正在被其他程序使用，请稍后重试") from exc
                    time.sleep(LOCK_INTERVAL)
        else:
            import fcntl
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            except OSError as exc:
                raise StorageError("账本正在被其他程序使用，请稍后重试") from exc

    @staticmethod
    def _release(handle):
        try:
            if os.name == "nt":
                import msvcrt
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass  # 句柄马上关闭，操作系统会一并释放锁。

    def _sync_directory(self):
        """让「换名」这条目录元数据真正落盘；Windows 不支持对目录 fsync，跳过。"""
        if os.name == "nt":
            return
        try:
            fd = os.open(str(self.path.parent), os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(fd)
        except OSError:
            pass
        finally:
            os.close(fd)
