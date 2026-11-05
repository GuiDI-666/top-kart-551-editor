#!/usr/bin/env python3
from collections import Counter
from pathlib import Path
import argparse
import time

from kart551_backend import Kart551Codec, find_server_encrypt_dir


def main():
    parser = argparse.ArgumentParser(description="批量调用 Top-Kart.dll 验证 551 文件")
    parser.add_argument("directory", nargs="?", type=Path)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    folder = args.directory or find_server_encrypt_dir()
    if not folder:
        raise SystemExit("未找到 EncryptKart")
    files = sorted(folder.glob("*.yml"))
    if args.limit:
        files = files[:args.limit]
    codec = Kart551Codec()
    counts = Counter(); failures = []; started = time.time()
    for index, path in enumerate(files, 1):
        try:
            doc = codec.read(path)
            counts[(doc.payload_start, len(doc.records))] += 1
        except Exception as exc:
            failures.append((path.name, str(exc)))
        if index % 100 == 0:
            print(f"{index}/{len(files)} ok={index-len(failures)} fail={len(failures)}", flush=True)
    print("files", len(files), "seconds", round(time.time() - started, 2))
    print("groups", dict(counts))
    print("failures", len(failures))
    for item in failures[:50]:
        print("FAIL", *item)


if __name__ == "__main__":
    main()
