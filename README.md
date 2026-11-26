# DynamoDB 查询 p95 周期性高点｜排查项目

**入口：** [阅读中文 HTML 报告](docs/index.html)。可直接用浏览器打开，无需构建、登录、JavaScript、外部样式或图床。

这是一份基于用户描述、本地候选仓储和 AWS 固定版本源码的分析，不是生产事故定案。没有连接生产集群、读取凭证、发 DynamoDB 请求，也没有修改服务或安装预热任务。

## 从哪里开始

1. **确认部署身份。** 对实际部署镜像导出的服务发布物运行（Python 3.10+）：

   `rtk python tools/inspect_deps.py "path/to/Service.deps.json"`

   脚本离线筛选 SDK 等相关包版本。不需要提供整份 deps、token 或服务配置。发布物可能采用单文件或仓储随应用源码编译：没有列出某个包不等于没用它。再核对实际加载的程序集信息版本、镜像 digest、provider 运行时类型与应用注册路径。
2. **观察一个对照组。** 先不预热、不主动取凭证，用相同版本记录至少 3 个预测窗口；按报告第 06 节对齐 owner、waiter、provider 和每页 HTTP 的时间段。
3. **只改一个变量。** 根据证据选择 v4 灰度、v3 临时预热实验或运行时/仓储方向；不要同时实施。把处理结果、样本数、剩余未知写回事故记录。

## 本地 HTTP 预览（可选）

在项目根目录运行 `rtk python -m http.server 8000 --bind 127.0.0.1 --directory docs`，浏览器打开 `http://127.0.0.1:8000/`，完成后 Ctrl+C。

## GitHub Pages

1. 先检查内部项目名、版本和故障场景是否允许公开；不要上传生产 trace、配置、凭证或原始日志。若不能公开，可仅在本地或受访问控制的系统内阅览。
2. 将**此文件夹**作为独立仓库上传，不要把整个工作区或业务源码上传。已准备静态发布目录 `docs/`，无需 Actions，也不依赖域名根路径。
3. 在仓库 **Settings → Pages → Build and deployment → Deploy from a branch**，选实际分支和 **/docs**，保存。用 Pages 设置页显示的网址访问。本项目未创建远端仓库、未推送、未公开发布。

[GitHub Pages 发布来源说明](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
