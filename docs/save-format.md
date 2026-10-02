# 已验证的战役存档结构

这是针对当前已验证 `Campaign.sav` 的实现说明，不是通用 Unreal 存档编辑器。
未知格式或原校验码不匹配时，程序拒绝写入。

## 定位字段

文件以 `GVAS` 开头。程序按完整属性标签唯一定位：

| 属性 | 类型 | 值字节数 |
| --- | --- | --- |
| CurrentMRP | UInt64Property | 8 |
| TotalMRP | UInt64Property | 8 |
| Checksum | UInt32Property | 4 |

已验证标签的布局：

```
int32(name_length + 1), ASCII name + NUL
int32(type_length + 1), ASCII type + NUL
uint32(0), uint32(value_size), byte(0), value
```

整数采用小端序。完整标签必须恰好出现一次。

## PackedData 与 CRC

从 `PackedData\0` 后找到 `ByteProperty\0`，长度位于后者起始位置加 22 字节。
长度值之后的字节区域是 CRC 输入。区域结束位置必须等于 `Checksum` 属性标签的起始位置。
两个 MRP 值必须完整落在此区域内。

```
Checksum = zlib.crc32(PackedData, 0x41916EBD)
```

`0x41916EBD` 是 Python zlib API 的初始 CRC 参数。
修改当前 MRP 后重新计算 CRC，再确认只有当前 MRP 的 8 字节以及校验码的 4 字节范围发生变化。

## 文件写入

先复制整个 SaveGames 并核对文件内容与 SHA-256，再检查源文件没有变化。
新战役存档写入原目录中的临时文件，执行 flush/fsync，再以 `os.replace` 原子替换。
写入后重新读取并解析，确认目标值、CRC 和其他存档。

已在本地用人工构造的数据验证数值边界、损坏校验码、备份、并发变化与游戏运行保护。
仓库不包含测试代码或实际游戏存档。
