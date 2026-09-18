# Round 3：540p 动画草稿

## 产物

- `agent-qualityops-draft-540p.mp4`：16:9 草稿，960×540，30fps，H.264 + AAC。
- `agent-qualityops-draft.srt`：53 段中文字幕；视频内已烧录同版字幕。
- `narration.json`：9 个场景的旁白、音频时长与时间轴。
- `audio/*.wav`：Windows 本地离线语音分段，仅用于继续剪辑。
- `agent-qualityops-narration-mix.wav`：中间混音文件，不进入发布压缩包。

## 真实性边界

- 画面中的指标来自 `docs/DEMO_EVIDENCE.json`，用于离线流程验证。
- 未运行真实模型，不代表真实模型效果提升。
- 未接入企业生产数据，也未声称企业部署。
- 为避免将项目旁白发送至外部服务，本轮改用 Windows 本地离线语音 `Microsoft Kangkang`。

## 已验证

- 容器时长：224.405 秒（约 3 分 44 秒）。
- 视频：H.264、960×540、30fps、6732 帧。
- 音频：AAC、48kHz；旁白混音峰值 0.8538，RMS 0.0831。
- 抽样检查 5 个场景，标题、数据卡、字幕和真实性声明均可读。
- 40 帧均匀抽样未发现黑帧。

## 复现

1. 运行 `video/scripts/generate_round3_audio_offline.ps1` 生成离线旁白。
2. 运行 `python video/scripts/render_round3_video.py` 生成 540p 草稿。
3. 依赖：Python、PyAV、Pillow、NumPy、SciPy、SoundFile；Windows 需有微软雅黑和本地中文语音。
