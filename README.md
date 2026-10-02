# ACE COMBAT 8 · MRP CONTROL

Windows 本地战役 MRP 修改器。默认目标 **2,000,000 MRP**，每次修改前自动备份全部存档，更新校验码并回读验证。

## 下载与运行

在本仓库的 [Releases](https://github.com/HosisoraLing/AC8-MRP-Editor/releases) 下载 `AC8-MRP-Editor-v1.0.0-windows-x64.zip`，解压整个文件夹，双击 `AC8-MRP-Editor.exe`。
不需要安装 Python。必须保留旁边的 `_internal` 文件夹。

1. 正常退出游戏，等待 Steam 云同步完成。
2. 确认自动检测到的 `SaveGames` 目录，也可以手动选择。
3. 输入目标 MRP，或点击「200 万」。支持 0～999,999,999 的整数。
4. 点击「备份并修改 MRP」，等待「修改完成 / VERIFIED」。
5. 再启动游戏，确认 MRP。

存档目录通过当前用户的 `LOCALAPPDATA` 定位：
`BANDAI NAMCO Entertainment/ACE COMBAT 8/Saved/SaveGames`。

备份保存在**程序目录的 `Backups/时间戳/`**，包含全部原始存档、SHA-256 清单和修改报告。
把程序解压到 D 盘，备份也会放在 D 盘。源码运行时，备份位于源码目录。

恢复时，先退出游戏并等待同步结束，再从相应备份的 `SaveGames` 文件夹中将 `Campaign.sav` 复制回游戏存档目录。
这会恢复该备份时刻的整个战役进度。

## 修改范围和保护

- 只修改 `Campaign.sav` 的 `CurrentMRP` 和 `Checksum`。
- 保留累计 MRP、装备、任务进度、文件长度和其他存档。
- 检查原校验码，备份后核对 SHA-256，再原子替换战役存档。
- 游戏正在运行、存档格式不兼容或写入前存档发生变化时停止操作。
- 写入后再次读取并验证数值与校验码。
- 深色前端支持高 DPI，缩小窗口后可滚动查看操作。

程序离线运行，不修改游戏可执行文件。兼容性基于已验证的存档结构；游戏更新改变结构后可能需要适配。

## 从源码运行

需要 Windows x64 和 Python 3.11（包含 Tkinter）。运行时仅使用 Python 标准库。

```powershell
python AC8_MRP_Editor.py
```

## 打包
构建可分发的便携程序：

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

构建环境、临时文件及输出都位于仓库目录：`.venv/`、`cache/`、`dist/`、`release/`。
构建时会安装固定版本的 PyInstaller；发布包包含程序、运行库、许可证、说明和 SHA-256 文件。

存档结构及校验码算法见 [docs/save-format.md](docs/save-format.md)。

## 开源许可

MIT。独立同人项目，与游戏开发商、发行商及官方服务没有关联。
本仓库只包含程序源码、文档和构建脚本，不包含测试代码、游戏文件、真实存档、备份或宣传片素材。
