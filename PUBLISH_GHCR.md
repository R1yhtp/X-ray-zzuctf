# 获取 GZCTF 能直接填写的镜像地址

这个包已经包含 GitHub Actions 自动构建配置。你的电脑不需要安装 Docker。
GitHub 会构建 linux/amd64 镜像、用随机测试 flag 启动它并完整解题，通过后推送 GHCR。
工作流使用 GitHub 自动提供的 GITHUB_TOKEN，不需要把个人 Token 填进源码。

## 1. 创建 GitHub 私有仓库

在 https://github.com/new 创建 **Private** 仓库，例如 `x-ray-challenge`。
工程包含官方解法，源码仓库请保持私有；容器镜像之后单独设为公开。

## 2. 上传解压后的文件

把本发布包解压后，其目录里的文件和文件夹上传到仓库根目录。
不要只上传 ZIP 文件，也不要让根目录多包一层 `x-ray/`。

仓库首页应能直接看到这些路径：

| 路径 | 作用 |
|---|---|
| `Dockerfile` | 构建容器 |
| `.github/workflows/publish-ghcr.yml` | 自动构建及推送工作流 |
| `app/` | 服务代码 |
| `rtl/` | SystemVerilog |
| `player/` | 选手文档 |
| `organizer/` | 解法和 WP，只在私有源码仓库保留 |
| `tools/` | 发布校验脚本 |

GitHub 网页可以拖入目录上传，注意包含 `.github` 和 `.dockerignore`。
提交到默认分支（通常为 `main`）。

## 3. 在 GitHub 构建并发布

打开仓库 **Actions**，选择 **Build and publish GHCR image**，点击 **Run workflow**。

默认输入无需修改：

| 输入 | 默认值 |
|---|---|
| image_path | `zzu2026/x-ray` |
| image_tag | `1.0` |

账号从当前仓库所有者自动读取并转小写，不需要修改 YAML。
例如仓库所有者如果是 `koyanrush`，成功发布后的地址为：

```text
ghcr.io/koyanrush/zzu2026/x-ray:1.0
```

这是命名示例，不表示镜像已经在该账号下发布。
以工作流成功后的 Summary 中显示的实际地址为准。

## 4. 允许 GZCTF 拉取

首次发布的 GHCR 镜像通常为私有。
在 GitHub 个人主页 **Packages → zzu2026/x-ray → Package settings**，
找到 **Change visibility → Public** 并确认。
这会公开容器镜像，源码仓库仍可保持 Private。

也可以保持镜像私有，在 GZCTF 配置有拉取权限的仓库凭据。
如果你只是要直接填写镜像地址，公开镜像操作更少。

## 5. 填入 GZCTF

| GZCTF 字段 | 值 |
|---|---|
| 容器镜像 | 复制工作流 Summary 中的完整镜像地址 |
| 服务端口 | `8000`，TCP |
| Flag 模板 | `zzuctf{[GUID]}` |
| CPU（0.1 核为单位） | 先设 `5` |
| 内存 | 先设 `256 MB` |

然后开启测试容器，通过平台分配的 URL 运行：

```bash
python organizer/solve.py http://平台分配的地址:外部端口 --out recovered
```

平台如果给的是 HTTPS 地址，直接使用该地址，不用额外拼端口。

## 工作流失败时

- **Actions 看不到工作流**：检查 `.github/workflows/publish-ghcr.yml` 在默认分支的仓库根目录。
- **构建失败**：打开 `Build linux/amd64 image` 步骤看错误。
- **通关检查失败**：工作流不会推送；打开 `Run image and recover its test flag` 的日志。
- **permission_denied: write_package**：若目标同名 package 以前由其他仓库创建，
  在 package 的 Manage Actions access 中授权当前仓库；也可改 image_path 为一个未用名称。
- **GZCTF 拉取失败**：检查 package 是否 Public，或平台是否配置了私有仓库凭据。

## 状态说明

作者环境已验证真实 RTL 与公开接口完整解题。
此发布配置在交付时尚未实际运行 GitHub Actions；镜像地址只有推送成功后才存在。

官方文档：
- https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images
- https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility
