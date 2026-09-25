#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""m1_sniff.py — 斐讯悟空 M1 (AirCat) 独立嗅探器（不依赖 Home Assistant）

用途：在把 aircat.phicomm.com 劫持到本机之前/之后，验证设备是否还在
尝试连接官方云、以及它上报的原始数据长什么样。

用法：
    python m1_sniff.py            # 监听 0.0.0.0:9000
    python m1_sniff.py 9001       # 自定义端口

工作方式：
    1. 监听 TCP 端口，等待 M1 连入（需先把 aircat.phicomm.com 的 DNS
       劫持到本机，或用 iptables/nftables 把发往官方云的流量重定向过来）；
    2. 对收到的每一帧回 ACK（激发设备持续上报）；
    3. 解析帧内 JSON（temperature/humidity/value/hcho）并以单行打印。
"""

import json
import socket
import sys
import threading

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
END_MARK = b"\xff#END#"
# 应答体：帧前 23 字节(设备头) + 以下固定内容，可激发设备持续上报
ACK_BODY = b'\x00\x18\x00\x00\x02{"type":5,"status":1}' + END_MARK

KEYS = (("温度", "temperature", "°C"),
        ("湿度", "humidity", "%"),
        ("PM2.5", "value", "µg/m³"),
        ("甲醛", "hcho", "µg/m³"))


def handle(conn, addr):
    print(f"[+] 设备连入: {addr[0]}:{addr[1]}")
    buf = b""
    try:
        while True:
            data = conn.recv(2048)
            if not data:
                print(f"[-] {addr[0]} 断开")
                break
            try:
                conn.sendall(data[:23] + ACK_BODY)   # ACK
            except OSError:
                break
            buf += data
            while END_MARK in buf:
                frame, buf = buf.split(END_MARK, 1)
                print_frame(frame)
    finally:
        conn.close()


def print_frame(frame: bytes) -> None:
    start, end = frame.find(b"{"), frame.find(b"}")
    if start < 0 or end <= start:
        return   # 心跳/注册帧，无数据键
    try:
        obj = json.loads(frame[start:end + 1])
    except json.JSONDecodeError:
        print(f"[?] 无法解析帧: {frame!r}")
        return
    parts = []
    for label, key, unit in KEYS:
        v = obj.get(key)
        if v is not None:
            parts.append(f"{label}={v}{unit}")
    print(f"[{addr_str}] " + "  ".join(parts) if parts else f"[?] 帧: {obj}")


addr_str = "M1"


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", PORT))
    srv.listen(5)
    print(f"[*] 嗅探器已启动，监听 0.0.0.0:{PORT}，等待悟空 M1 连入…")
    print(f"[*] 前提：aircat.phicomm.com 已解析到本机（DNS 劫持）")
    try:
        while True:
            conn, addr = srv.accept()
            global addr_str
            addr_str = addr[0]
            threading.Thread(target=handle, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\n[*] 退出")
    finally:
        srv.close()


if __name__ == "__main__":
    main()
