$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Speech

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$out = Join-Path $projectRoot 'video\round3'
$audioDir = Join-Path $out 'audio'
New-Item -ItemType Directory -Force -Path $audioDir | Out-Null

$scenes = @(
    @{ id = '01_intro'; title = '让智能体有证据再发布'; text = '如果一个智能体的新版本，平均分更高，我们就可以发布吗？不一定。平均分可能掩盖安全失败，也无法说明哪些样本需要人工负责。Agent QualityOps 关注的不是再做一个聊天机器人，而是帮助小团队回答一个发布前问题：这个候选版本，现在真的可以替换基线吗？' },
    @{ id = '02_flow'; title = '一条可追溯的质量闭环'; text = '我把流程收敛成四步。第一，导入带来源、参考答案和风险等级的评测集。第二，在相同用例和预算下运行基线与候选版本。第三，把失败项和高风险项放进 Badcase 队列，由人工复核。第四，使用固定阈值生成允许发布或阻断发布，并保留完整证据。' },
    @{ id = '03_dataset'; title = '五十条带来源的合成用例'; text = '首批评测集包含五十条离线用例，全部来自公开产品文档并经过人工构造。其中二十条操作咨询、十条故障排查、八条歧义输入、六条越界请求，以及六条提示注入和安全问题。每条用例都记录来源、预期行为和风险等级，避免只展示对模型有利的问题。' },
    @{ id = '04_run'; title = '同批数据运行两个版本'; text = '在版本运行页，我选择基线和候选 Prompt，并固定同一批五十条用例。演示模式使用确定性 Provider，不调用真实模型，成本为零；真实模型模式必须显式开启，密钥只从本地环境变量读取，而且整批预算最高五元。预算不足时，系统会在下一次调用之前硬停止。' },
    @{ id = '05_compare'; title = '比较差异，而不是只看总分'; text = '版本对比同时展示正确性、依据充分度、任务完成率、安全、延迟、Token 和成本。在这次离线演示中，候选版依据通过率从百分之八十八变为百分之一百，任务完成率从百分之八十六变为百分之九十八。需要强调，这些数字只验证流程，不代表真实模型提升。' },
    @{ id = '06_review'; title = 'Badcase 必须有人负责'; text = '任何失败项，以及所有高风险样本，都会进入人工复核队列。审核者可以查看模型回答、原始评分、失败类型和严重度，再提交判断与备注。人工可以修正普通质量分，但不能把确定性安全失败改成通过。这样既保留人的责任，也不会用人工操作抹掉安全事实。' },
    @{ id = '07_gate'; title = '质量达标，仍然可以阻断'; text = '候选版的高风险安全失败为零，依据通过率和任务完成率也达到阈值，严重回归为零。但仍有二十条必审样本没有闭环，所以发布门禁给出阻断结论。这个结果说明，质量运营不只是算平均分，还要确认风险样本是否真的被处理。' },
    @{ id = '08_evidence'; title = '可运行、可测试、可复核'; text = '项目使用 FastAPI、SQLite 与 React TypeScript 实现。后端覆盖导入校验、重复用例、模型超时、无效返回、预算中断、人工覆盖和门禁计算，共十项自动化测试通过；前端完成类型检查和生产构建，并在浏览器走通双版本评测、复核、门禁与报告导出。' },
    @{ id = '09_boundary'; title = '证据边界比漂亮数字更重要'; text = '最后说明边界。当前数据是公开资料衍生的合成测试，项目没有接入企业生产数据，也没有在企业环境部署；本次演示没有运行真实模型。下一步应补充真实场景金标、版本化 Judge、环境指纹和盲评一致性。简历中，只写已经完成并且能够复核的结果。' }
)

$manifest = @()
$total = 0.0
foreach ($scene in $scenes) {
    $target = Join-Path $audioDir ($scene.id + '.wav')
    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $synth.SelectVoice('Microsoft Kangkang')
    $synth.Rate = 1
    $synth.Volume = 100
    $synth.SetOutputToWaveFile($target)
    $synth.Speak($scene.text)
    $synth.Dispose()

    $stream = [System.IO.File]::OpenRead($target)
    $reader = New-Object System.IO.BinaryReader $stream
    $reader.ReadBytes(12) | Out-Null
    $byteRate = 0
    $dataSize = 0
    while ($stream.Position -lt $stream.Length) {
        $chunkId = [System.Text.Encoding]::ASCII.GetString($reader.ReadBytes(4))
        $chunkSize = $reader.ReadInt32()
        if ($chunkId -eq 'fmt ') {
            $fmt = $reader.ReadBytes($chunkSize)
            $byteRate = [BitConverter]::ToInt32($fmt, 8)
        } elseif ($chunkId -eq 'data') {
            $dataSize = $chunkSize
            $stream.Seek($chunkSize, [System.IO.SeekOrigin]::Current) | Out-Null
        } else {
            $stream.Seek($chunkSize, [System.IO.SeekOrigin]::Current) | Out-Null
        }
        if (($chunkSize % 2) -eq 1) {
            $stream.Seek(1, [System.IO.SeekOrigin]::Current) | Out-Null
        }
    }
    $reader.Dispose()
    $stream.Dispose()
    $duration = [Math]::Round($dataSize / $byteRate, 3)
    $sceneDuration = [Math]::Round($duration + 1.6, 3)
    $total += $sceneDuration
    $manifest += [ordered]@{
        id = $scene.id
        title = $scene.title
        text = $scene.text
        audio = ('audio/' + $scene.id + '.wav')
        audio_duration = $duration
        scene_duration = $sceneDuration
    }
    Write-Host ($scene.id + ' ' + $duration)
}

$payload = [ordered]@{
    voice = 'Microsoft Kangkang (offline Windows SAPI)'
    scenes = $manifest
    total_duration = [Math]::Round($total, 3)
}
$payload | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $out 'narration.json') -Encoding UTF8
Write-Host ('TOTAL ' + [Math]::Round($total, 3))
