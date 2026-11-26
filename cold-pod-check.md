# 冷 Pod：一次查询有没有调用凭证端点？

只回答这个问题。APM 采样 10%，不用调高，也不必等它采中：以下用 dotnet-trace 直接订阅业务进程的 System.Net.Http 事件。只发一次真实业务请求，不手动 curl 凭证端点，不等一小时。

## 1. 固定 Pod，装一个工具

选刚 Ready、不接普通流量的 test Pod。在本机 PowerShell 终端 A 设置四项，启动转发，并保持窗口打开：

```powershell
$ns = '替换为测试命名空间'
$pod = '替换为冷Pod名'
$port = 8080  # 改成业务容器实际监听的端口
kubectl -n $ns port-forward "pod/$pod" "18080:$port"
```

另开本机 PowerShell 终端 B，设置变量后进入同一 Pod 的业务容器：

```powershell
$ns = '替换为相同的测试命名空间'
$pod = '替换为相同的冷Pod名'
$app = '替换为业务容器名'
kubectl -n $ns exec -it $pod -c $app -- sh
```

在 Pod 内执行（Linux、可执行且可写的 /tmp、有 curl；无需完整 SDK）：

```sh
umask 077
cd /tmp || exit 1
case "$(uname -m)" in x86_64) arch=x64;; aarch64|arm64) arch=arm64;; *) echo '请按架构选择微软官方下载'; exit 1;; esac
rid=linux-$arch
[ ! -f /etc/alpine-release ] || rid=linux-musl-$arch
curl -fL "https://aka.ms/dotnet-trace/$rid" -o dotnet-trace && chmod 700 dotnet-trace && ./dotnet-trace ps
```

认出**业务应用 PID**，不默认是 1。若 Pod 无外网或无 curl，在电脑从相同微软地址下载匹配的 Linux 工具，用 kubectl cp 传入 /tmp，再 chmod 700。若镜像没有 shell/tar，请用平台已有诊断镜像，不要提权。

## 2. 先开始录，再发一次查询

在 Pod 内执行，把 123 换成上一步 PID：

```sh
./dotnet-trace collect -p 123 --providers 'System.Net.Http:0xFFFFFFFF:4' --duration 00:00:01:00 -o /tmp/cold-ddb.nettrace
```

等看到 **Recording trace**，再用 Postman 向转发端口 localhost:18080 发一次原业务接口请求（沿用实际协议、路径、鉴权）。选一组未缓存且能实际访问 DynamoDB 的 hash key + range key，关闭客户端重试。记下发送时间，等 60 秒采集结束。不要为了在 APM 里看到它而重复发，第二次已经不是同一次冷查询。

## 3. 拷出，看两个 HTTP 事件

在终端 B 输入 exit 返回本机 PowerShell，再执行（kubectl cp 需要容器有 tar）：

```powershell
kubectl -n $ns cp "${pod}:/tmp/cold-ddb.nettrace" .\cold-ddb.nettrace -c $app
```

Windows：用 PerfView 打开 cold-ddb.nettrace → **Events** → 筛选 **System.Net.Http/Request/Start**（也可搜 RequestStart）→ **Update**。看发送业务请求那几秒的时间、host 和 pathAndQuery；隔离 Pod 若同时有后台 AWS 调用，不能仅凭先后就归给业务请求。

| 本地文件里看到什么 | 怎么记结果 |
|---|---|
| 先是凭证端点（host 匹配，路径可见时为 /v1/credentials），然后是 DynamoDB 端点 | 在只有这一次 AWS 业务调用的前提下，确认这次查询先请求了凭证，再查 DDB。记录两条 RequestStart 的时间。 |
| 只有 DynamoDB 端点 | 记“查库了，这次未观察到凭证 HTTP”。新 Pod 可能在工具附加前已取过凭证。 |
| 连 DynamoDB 出站事件都没有 | 这份采集不能作判断：先核对 Pod、PID、录制时间和业务 key。APM 有没有记录都不改变这个结论。 |

这份采集不用于证明等待了凭证锁；两个出站事件的时间差也不是业务入口到取凭证的耗时。原始文件留在受控环境，不上传公开仓库；不记录 token、请求头或凭证响应。

[微软：dotnet-trace 下载与参数](https://learn.microsoft.com/en-us/dotnet/core/diagnostics/dotnet-trace) · [微软：HTTP 网络事件](https://learn.microsoft.com/en-us/dotnet/fundamentals/networking/telemetry/events)
