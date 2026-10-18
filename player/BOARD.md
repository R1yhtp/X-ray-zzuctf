# LA-4 板卡与逻辑分析仪

## 硬件资料

- 面板为 192 × 64 单色像素，两个显存 bank，各 768 个 16 位字。
- `display_core.sv` 包含 DMA、显存及扫描输出。
- 板上维护字库以点阵存储，通过 ROM 数据端口交给 DMA。
- 本地资料包含公开预览 ROM。线上 ROM 不通过文件接口提供。
- 字符排版：原点 `(6,14)`，字符步进 `(6,10)`，每行 30 个字符。

## 探针

每次最多连接四组探针；向量信号算一组。

| 名称 | 位宽 | 电气名称 |
|---|---:|---|
| tx_valid | 1 | DMA 请求 |
| tx_ready | 1 | 显存响应 |
| tx_bank | 1 | 目标 bank |
| tx_mask | 2 | 字节使能 |
| tx_addr | 10 | 字地址 |
| tx_data | 16 | 写数据 |
| hsync | 1 | 行同步，低有效 |
| vsync | 1 | 场同步，低有效 |
| pixel | 1 | 前台像素输出 |
| fence | 1 | DMA 阶段边界 |
| hpos | 8 | 扫描列 |
| vpos | 7 | 扫描行 |

波形只包含选定探针与采样标记，不支持任意层次路径。

## 采集语义

- 仿真窗口：复位释放后的 32768 个像素时钟周期。
- 在 DUT 时钟上升沿之前锁存信号，VCD `sample` 从 0 变 1 表示一条完整记录。
- 同一时间戳下先更新探针值，再升高 `sample`；空白时间段不表示信号没有变化。
- `clock`：每个时钟周期生成一个候选事件。
- `activity`：只在 `tx_valid=1` 的周期生成候选事件。此模式不等于成功写入触发。
- `vblank`：只在场同步有效期间生成候选事件。
- `start`：跳过的候选事件数，从 0 起。
- `count`：本次最多记录的事件数，1～1024。
- VCD 使用绝对仿真时间；`start` 是触发后的事件序号，不是纳秒数。
- `acquisition.json` 返回本次记录数、完整窗口中的候选事件总数和实例标识。
- 采集不消耗尝试次数。一次实例同时运行一项采集，忙时返回 HTTP 429。

## HTTP 接口

`GET /api/info` 返回探针能力和实例标识。

`POST /api/capture`，请求类型为 `application/json`：

```json
{"probes":["tx_valid","tx_ready","tx_bank","tx_mask"],"trigger":"activity","start":0,"count":1024}
```

响应是 ZIP，包含 `capture.vcd` 和 `acquisition.json`。

可用 Python 标准库调用；也可使用：

```bash
curl -X POST http://127.0.0.1:8000/api/capture \
  -H 'Content-Type: application/json' \
  --data '{"probes":["tx_addr","tx_data"],"trigger":"activity","start":0,"count":1024}' \
  -o capture.zip
```

HTTP/HTTPS、主机及外部端口以比赛平台分配的地址为准。
