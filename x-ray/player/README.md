# X-ray

旧显示板的维护图案一闪而过。接上探针，找回屏幕没留下的东西。

- 分类：Misc / 硬件波形分析
- Flag 格式：`zzuctf{...}`，注意大小写。
- 浏览器访问平台分配的地址，下载板卡资料，配置并运行逻辑分析仪。
- `capture.vcd` 可在 GTKWave 中打开，也可编写脚本处理。
- `BOARD.md` 是接口及采集语义说明。`rtl/` 是实际运行的逻辑与采集器。
- `preview.mem` 仅供本地仿真，内容是公开演示图案；线上存储器独立配置。
- `font5x7.json` 是板卡字符集：每字形 7 行，每行 5 位，最高位在左。

本地验证：安装 Icarus Verilog，在此目录运行：

```bash
iverilog -g2012 -s analyzer_tb -o sim.vvp rtl/display_core.sv rtl/analyzer_tb.sv
vvp sim.vvp +rom=preview.mem +out=preview.vcd +probes=63 +trigger=1 +skip=0 +take=1024
```

上例是本地仪器测试，线上每次最多连接四组探针。
线上波形由容器中的真实 RTL 仿真产生；每次采集都从同一上电状态重放，
因此同一实例、相同触发模式下，不同探针的绝对时间戳可以对齐。

重启容器后请重新下载采集结果，勿混用不同实例的数据。
