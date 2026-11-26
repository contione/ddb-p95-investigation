# DynamoDB 查询 p95 周期性高点｜排查项目

**入口：** [公开 Pages 报告](https://contione.github.io/ddb-p95-investigation/)。本地可直接打开 [HTML 报告](docs/index.html)，无需构建、登录或外部资源。

这是一份基于用户描述、本地候选仓储和 AWS 固定版本源码的分析，不是生产事故定案。没有连接生产集群、读取凭证或发 DynamoDB 请求，也没有修改服务或安装预热任务。

## 当前结论

- 观测到实际 DynamoDB 回源量平稳，没有缓存整体击穿的证据。平稳回源也不能证明不存在同 key 等待者，但目前不足以把缓存记为放大因素。
- 没有证据表明贴出的 `GetOrSetAsync` 路径发生死锁；不要把第一个慢查询或跟随者延迟直接命名为缓存锁死锁。
- 首要验证方向是凭证刷新链路：按真实请求记录 factory、provider、token/agent HTTP 和 DynamoDB attempt 的时间，先区分刷新发起、等待、调度和上游排队，再决定是否做版本或预热实验。
- `AWSSDK.DynamoDBv2 3.7.406.23` 是项目声明/依赖清单中的 DynamoDBv2 包号，不是线上 `AWSSDK.Core` 版本的证据。线上版本必须以部署镜像的 `.deps.json`、实际加载的程序集信息、镜像 digest 和 provider 类型为准。

## 从哪里开始

1. **确认部署身份。** 对实际部署镜像导出的服务发布物运行（Python 3.10+）：

   `rtk python tools/inspect_deps.py "path/to/Service.deps.json"`

   脚本离线筛选 SDK 等相关包版本。不需要提供整份 deps、token 或服务配置。发布物可能采用单文件或仓储随应用源码编译：没有列出某个包不等于没用它。再核对实际加载的程序集信息版本、镜像 digest、provider 运行时类型与应用注册路径。
2. **观察一个对照组。** 先不预热、不主动取凭证，用相同版本记录至少 3 个预测窗口；按报告第 06 节对齐 owner、waiter、provider 和每页 HTTP 的时间段。
3. **只改一个变量。** 先验证刷新链路，再根据证据选择兼容的 v4 灰度、v3 临时预热对照或运行时/仓储方向；不要把预热当作默认修复，也不要同时实施多个变量。把处理结果、样本数、剩余未知写回事故记录。

## 本地 HTTP 预览（可选）

在项目根目录运行 `rtk python -m http.server 8000 --bind 127.0.0.1 --directory docs`，浏览器打开 `http://127.0.0.1:8000/`，完成后 Ctrl+C。

## GitHub Pages

1. 先检查内部项目名、版本和故障场景是否允许公开；不要上传生产 trace、配置、凭证或原始日志。若不能公开，可仅在本地或受访问控制的系统内阅览。
2. 将**此文件夹**作为独立仓库上传，不要把整个工作区或业务源码上传。已准备静态发布目录 `docs/`，无需 Actions，也不依赖域名根路径。
3. 在仓库 **Settings → Pages → Build and deployment → Deploy from a branch**，选实际分支和 **/docs**，保存。公开入口是仓库 Pages 根 URL：`https://contione.github.io/ddb-p95-investigation/`；不要把 `docs/index.html` 当作公开站点入口。

[GitHub Pages 发布来源说明](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
