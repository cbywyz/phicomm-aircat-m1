"""Constants for phicomm_aircat."""

DOMAIN = "phicomm_aircat"

# 悟空 M1 监听端口（固件硬编码 aircat.phicomm.com:9000）
PORT = 9000

# 帧结尾标记
END_MARK = b"\xff#END#"

# 服务器心跳 ACK：前 23 字节(设备头) + 此串，可激发设备上报数据
HEARTBEAT_ACK = b'\x00\x18\x00\x00\x02{"type":5,"status":1}' + END_MARK
