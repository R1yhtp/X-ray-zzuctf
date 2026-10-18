# X-ray

GZCTF 动态容器 Misc，软硬件交叉 / SystemVerilog / 逻辑分析仪 / VCD。
设计定位为中高难；尚未经过真人赛测，实际难度需根据参赛群体调整。

**需要 `ghcr.io/...:版本` 镜像地址：优先看 `PUBLISH_GHCR.md`。**
工程已附 GitHub Actions，可在 GitHub 自动构建、通关检查并发布镜像，不需要本地 Docker。

## 一句话题面

> 旧显示板的维护图案一闪而过。接上探针，找回屏幕没留下的东西。

## 玩法与核心

选手拿到公开 RTL、板卡接口文档及演示 ROM，通过网页或 HTTP API 配置四组探针。
每次采集由 Icarus Verilog 的 `vvp` 实际执行已编译的 SystemVerilog，返回 VCD。
选手需要对齐多次采集，识别 ready/valid 握手、应用字节使能、还原平铺蛇形地址，
从写入历史截取后台缓冲区擦除前的点阵，读出完整 flag。

动态 flag 整体绘制进一个点阵画面，不分段拼接；总线没有明文字符流。
正常 `pixel` 输出只看到前台测试图案；最终后台缓冲区也已清空。
本项目为全新实现，借鉴 UIUCTF 2025 X_Ray 的硬件观测思路，没有复制其源码或附件。

## 本地 Docker 测试

```bash
cp .env.example .env
docker compose up --build -d
```

打开 `http://127.0.0.1:8000`。官方脚本只依赖 Python 3.10+ 标准库：

```bash
python3 organizer/solve.py http://127.0.0.1:8000 --out recovered
```

输出应与 `.env` 中的本地测试 flag 完全相同，并生成 `recovered.png`。
`final-buffer.png` 应为全黑。这两个结果验证“历史中有图，最终显存无图”。

无 Docker 时可安装 Icarus Verilog 12+，再运行：

```bash
sh tools/build_local.sh
GZCTF_FLAG='zzuctf{local_scope_test_4b7d1c29}' python3 app/server.py
```

服务端只用 Python 标准库，不需要 pip 安装依赖。
`IVERILOG`、`VVP`、`SIM_EXECUTABLE` 可用于指定本地仿真工具路径；线上无需设置。

## GZCTF 配置

| 项目 | 设置 |
|---|---|
| 类别 | Misc |
| 类型 | 动态容器（界面名称以平台版本为准） |
| 镜像 | 自己构建并推送的 `registry.example.com/ctf/x-ray:1.0` |
| 服务端口 | **8000 / TCP**，浏览器 HTTP 服务 |
| 动态 flag 模板 | **`zzuctf{[GUID]}`** |
| CPU 限制（0.1 CPUs 为单位） | 先填 **5**，即 0.5 核，再根据实测调整 |
| 内存 | 先设 **256 MB**，再根据实测调整 |
| 存储 | 以构建后镜像实际占用加余量设置；建议先预留 512 MB，超限则上调 |
| 网络 | 服务无运行时外网依赖；可使用平台隔离网络并由平台映射访问端口 |
| 流量捕获 | 可选，不参与题目逻辑 |

GZCTF 在容器启动时注入 `GZCTF_FLAG`。本程序要求 `zzuctf{}` 格式，
花括号内支持 1～80 个英文字母、数字、下划线或连字符；上述 GUID 模板受支持。
未设置或格式错误时启动失败，避免意外用演示 flag 开赛。

构建并推送（将示例仓库改成你自己的）：

```bash
docker build --platform linux/amd64 -t x-ray:1.0 .
docker tag x-ray:1.0 registry.example.com/ctf/x-ray:1.0
docker login registry.example.com
docker push registry.example.com/ctf/x-ray:1.0
```

平台保存镜像配置后，启动测试容器，使用平台分配的 URL 执行官方脚本。
GZCTF 不读取本地 `compose.yml`；Compose 仅用于你自己的本地测试。

如果管理员要求提供镜像文件：

```bash
docker save -o x-ray-image.tar x-ray:1.0
```

此命令产生镜像归档；发布包内的 Dockerfile/源码 ZIP 本身不是 Docker 镜像。
镜像仓库如需认证，应在 GZCTF 配置相应凭据。

## 文件分发

- **选手：** 题面、平台启动的环境、`x-ray-player.zip`。
- **主办方：** 本完整工程及 `organizer/`；请保留解法和测试资料。
- 环境也可直接下载选手附件，因此外部平台无需额外挂文件也能开题。
- `.dockerignore` 采用允许清单，官方解法与测试不会进入镜像。

## 验证与维护

```bash
python3 tests/integration.py
```

详细出题原理、非预期解审查范围与可调整项见 `organizer/WRITEUP.md`。
发布前在实际 GZCTF 上复测镜像拉取、端口转发、动态 flag 与资源限额。

## 参考与归属

- X_Ray 赛题资料与一手复现：
  https://gist.github.com/rafael-borecki/b8a2ee43f5ca00259bf8653890e02903
- UIUCTF 官方题库：https://github.com/sigpwny/UIUCTF-2025-Public
- Icarus Verilog：https://steveicarus.github.io/iverilog/usage/simulation.html
- GZCTF 动态 flag：https://gzctf.gzti.me/guide/features/dynamic-flag

本工程源码采用 MIT 许可证。上述原题和工具的权利归各自作者所有。
