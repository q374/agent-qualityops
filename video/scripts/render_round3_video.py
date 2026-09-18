from __future__ import annotations

import json
import math
import re
import wave
from fractions import Fraction
from pathlib import Path

import av
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont
from scipy.signal import resample_poly


ROOT = Path(__file__).resolve().parents[2]
ROUND3 = ROOT / "video" / "round3"
MANIFEST = ROUND3 / "narration.json"
OUT_VIDEO = ROUND3 / "agent-qualityops-draft-540p.mp4"
OUT_WAV = ROUND3 / "agent-qualityops-narration-mix.wav"
OUT_SRT = ROUND3 / "agent-qualityops-draft.srt"

W, H, FPS, SR = 960, 540, 30, 48_000
BG = (8, 20, 18)
PANEL = (15, 33, 29)
PANEL_2 = (20, 43, 37)
LINE = (52, 79, 68)
TEXT = (238, 246, 240)
MUTED = (157, 176, 166)
LIME = (184, 255, 96)
GREEN = (67, 211, 142)
AMBER = (255, 190, 75)
RED = (255, 104, 112)
CYAN = (83, 204, 220)

FONT_REG = r"C:\Windows\Fonts\msyh.ttc"
FONT_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"


def font(size: int, bold: bool = False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


F12 = font(12)
F14 = font(14)
F16 = font(16)
F18 = font(18)
F20 = font(20, True)
F24 = font(24, True)
F30 = font(30, True)
F42 = font(42, True)
F50 = font(50, True)


def clamp(v: float, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def ease(v: float):
    v = clamp(v)
    return 1 - (1 - v) ** 3


def rounded(draw, xy, radius=16, fill=PANEL, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def pill(draw, xy, text, fill, fg=BG, f=F14):
    x, y = xy
    box = draw.textbbox((0, 0), text, font=f)
    w = box[2] - box[0] + 24
    h = box[3] - box[1] + 14
    rounded(draw, (x, y, x + w, y + h), h // 2, fill)
    draw.text((x + 12, y + 5), text, font=f, fill=fg)
    return w, h


def wrap_text(draw, text, f, max_width):
    lines, buf = [], ""
    for ch in text:
        candidate = buf + ch
        if draw.textlength(candidate, font=f) <= max_width or not buf:
            buf = candidate
        else:
            lines.append(buf)
            buf = ch
    if buf:
        lines.append(buf)
    return lines


def draw_header(draw, index, title, accent=LIME):
    draw.text((38, 24), "AGENT QUALITYOPS", font=F14, fill=accent)
    draw.text((38, 50), title, font=F30, fill=TEXT)
    draw.text((880, 26), f"{index:02d} / 09", font=F14, fill=MUTED)
    draw.line((38, 94, 922, 94), fill=LINE, width=1)


def base_image():
    arr = np.zeros((H, W, 3), dtype=np.uint8)
    for y in range(H):
        t = y / H
        arr[y, :, 0] = int(BG[0] + 4 * t)
        arr[y, :, 1] = int(BG[1] + 10 * t)
        arr[y, :, 2] = int(BG[2] + 7 * t)
    # 轻微网格，保持企业仪表盘质感
    arr[::36, :, :] = np.maximum(arr[::36, :, :], np.array([13, 32, 28], dtype=np.uint8))
    arr[:, ::48, :] = np.maximum(arr[:, ::48, :], np.array([12, 29, 26], dtype=np.uint8))
    return Image.fromarray(arr, "RGB")


def progress_bar(draw, x, y, w, value, color, label, value_text):
    draw.text((x, y), label, font=F16, fill=MUTED)
    draw.text((x + w, y), value_text, font=F16, fill=TEXT, anchor="ra")
    rounded(draw, (x, y + 28, x + w, y + 40), 6, (32, 53, 46))
    rounded(draw, (x, y + 28, x + int(w * clamp(value)), y + 40), 6, color)


def scene_1(draw, p):
    draw_header(draw, 1, "发布前，不只看平均分")
    a = ease(p / 0.25)
    x = int(55 + (1 - a) * 70)
    draw.text((x, 128), "让智能体", font=F50, fill=TEXT)
    draw.text((x, 190), "有证据再发布", font=F50, fill=LIME)
    draw.text((x, 265), "一个面向小团队的评测、Badcase 与发布门禁闭环", font=F18, fill=MUTED)
    rounded(draw, (610, 130, 890, 368), 20, PANEL, LINE)
    draw.text((640, 158), "RELEASE GATE", font=F14, fill=MUTED)
    draw.text((640, 196), "候选版本", font=F20, fill=TEXT)
    gate_p = ease((p - 0.35) / 0.2)
    status = "BLOCKED" if gate_p > 0.45 else "CHECKING"
    color = RED if status == "BLOCKED" else AMBER
    pill(draw, (640, 238), status, color)
    draw.text((640, 295), "平均分更高 ≠ 可以发布", font=F16, fill=TEXT)
    draw.text((640, 328), "安全失败 · 必审闭环 · 严重回归", font=F14, fill=MUTED)


def scene_2(draw, p):
    draw_header(draw, 2, "一条可追溯的质量闭环")
    items = [
        ("01", "导入评测集", "来源 / 金标 / 风险"),
        ("02", "双版本运行", "同用例 / 同预算"),
        ("03", "复核 Badcase", "失败项 / 高风险"),
        ("04", "发布门禁", "允许 / 阻断 / 证据"),
    ]
    for i, (num, title, sub) in enumerate(items):
        x = 45 + i * 226
        local = ease((p - i * 0.12) / 0.22)
        y = int(150 + (1 - local) * 55)
        active = int(p * 4.2) >= i
        rounded(draw, (x, y, x + 188, y + 230), 18, PANEL_2 if active else PANEL, LIME if active else LINE, 2 if active else 1)
        pill(draw, (x + 18, y + 18), num, LIME if active else LINE, BG if active else TEXT)
        draw.text((x + 18, y + 79), title, font=F20, fill=TEXT)
        lines = wrap_text(draw, sub, F14, 150)
        for j, line in enumerate(lines):
            draw.text((x + 18, y + 121 + j * 25), line, font=F14, fill=MUTED)
        if i < 3:
            draw.line((x + 191, y + 112, x + 222, y + 112), fill=GREEN if active else LINE, width=3)
            draw.polygon([(x + 217, y + 106), (x + 225, y + 112), (x + 217, y + 118)], fill=GREEN if active else LINE)
    draw.text((45, 421), "每个结论都能回到版本、用例、运行时间、成本与人工判断", font=F16, fill=LIME)


def scene_3(draw, p):
    draw_header(draw, 3, "50 条带来源的合成用例")
    rounded(draw, (38, 122, 310, 420), 20, PANEL, LINE)
    draw.text((66, 148), "EVAL SET", font=F14, fill=MUTED)
    draw.text((66, 195), "50", font=F50, fill=LIME)
    draw.text((66, 258), "公开资料衍生 · 离线验证", font=F16, fill=TEXT)
    pill(draw, (66, 310), "非企业真实数据", AMBER)
    draw.text((66, 363), "来源、预期行为、风险等级", font=F14, fill=MUTED)
    items = [
        ("操作咨询", 20, LIME), ("故障排查", 10, GREEN), ("歧义输入", 8, CYAN),
        ("越界请求", 6, AMBER), ("提示注入 / 安全", 6, RED),
    ]
    for i, (label, n, color) in enumerate(items):
        y = 133 + i * 58
        draw.text((355, y), label, font=F16, fill=TEXT)
        draw.text((892, y), str(n), font=F16, fill=TEXT, anchor="ra")
        rounded(draw, (355, y + 26, 890, y + 38), 6, (30, 51, 44))
        fill = int(535 * (n / 20) * ease((p - i * 0.07) / 0.35))
        if fill > 2:
            rounded(draw, (355, y + 26, 355 + fill, y + 38), 6, color)
    draw.text((355, 432), "刻意加入不利样本，避免只展示模型擅长的问题", font=F15 if False else F14, fill=MUTED)


def scene_4(draw, p):
    draw_header(draw, 4, "同批数据运行两个版本")
    cards = [(55, "BASELINE", "Prompt v1", GREEN), (505, "CANDIDATE", "Prompt v2", LIME)]
    for i, (x, label, version, color) in enumerate(cards):
        rounded(draw, (x, 130, x + 400, 380), 20, PANEL, color if i == 1 else LINE, 2 if i == 1 else 1)
        draw.text((x + 26, 155), label, font=F14, fill=color)
        draw.text((x + 26, 194), version, font=F24, fill=TEXT)
        pill(draw, (x + 26, 241), "确定性 Demo Provider", LINE, TEXT)
        progress_bar(draw, x + 26, 300, 345, ease((p - i * 0.12) / 0.55), color, "50 条用例", "50 / 50")
    pill(draw, (55, 407), "¥0 演示成本", LIME)
    draw.text((214, 415), "真实模型需显式开启 · 密钥仅本地环境变量 · 预算硬上限 ¥5", font=F14, fill=MUTED)


def scene_5(draw, p):
    draw_header(draw, 5, "比较差异，而不是只看总分")
    rounded(draw, (40, 120, 920, 422), 20, PANEL, LINE)
    metrics = [
        ("依据通过率", 0.88, 1.00),
        ("任务完成率", 0.86, 0.98),
        ("高风险安全失败", 0.00, 0.00),
        ("严重回归", 0.00, 0.00),
    ]
    for i, (label, old, new) in enumerate(metrics):
        y = 150 + i * 62
        draw.text((67, y + 7), label, font=F16, fill=TEXT)
        if i < 2:
            draw.text((310, y + 7), f"{int(old*100)}%", font=F14, fill=MUTED)
            rounded(draw, (355, y + 11, 720, y + 23), 6, (35, 55, 48))
            rounded(draw, (355, y + 11, 355 + int(365 * old), y + 23), 6, GREEN)
            width = int(365 * new * ease((p - 0.15) / 0.5))
            rounded(draw, (355, y + 31, 355 + width, y + 43), 6, LIME)
            draw.text((748, y + 23), f"{int(new*100)}%", font=F16, fill=LIME)
        else:
            pill(draw, (310, y), "0", LIME)
            draw.text((380, y + 7), "满足默认门槛", font=F14, fill=MUTED)
    pill(draw, (64, 368), "重要边界", AMBER)
    draw.text((182, 376), "离线 Demo 数字只验证流程，不代表真实模型提升", font=F16, fill=TEXT)


def scene_6(draw, p):
    draw_header(draw, 6, "Badcase 必须有人负责")
    rounded(draw, (38, 118, 430, 430), 18, PANEL, LINE)
    draw.text((62, 142), "BADCASE QUEUE", font=F14, fill=MUTED)
    rows = [
        ("SAFE-006", "提示注入", "HIGH", RED),
        ("AMB-003", "信息不足", "MEDIUM", AMBER),
        ("OPS-012", "依据缺失", "LOW", CYAN),
    ]
    for i, (case, typ, sev, color) in enumerate(rows):
        y = 182 + i * 72
        active = i == min(2, int(p * 3.2))
        rounded(draw, (57, y, 410, y + 58), 10, PANEL_2 if active else (18, 38, 33), color if active else LINE)
        draw.text((73, y + 9), case, font=F16, fill=TEXT)
        draw.text((73, y + 34), typ, font=F12, fill=MUTED)
        pill(draw, (320, y + 13), sev, color, BG, F12)
    rounded(draw, (458, 118, 922, 430), 18, PANEL, LIME, 2)
    draw.text((484, 142), "人工复核", font=F20, fill=TEXT)
    draw.text((484, 184), "模型回答", font=F14, fill=MUTED)
    rounded(draw, (484, 208, 895, 267), 10, (20, 43, 37), LINE)
    draw.text((500, 224), "原始评分、失败类型、严重度与证据", font=F14, fill=TEXT)
    pill(draw, (484, 294), "提交判断", LIME)
    pill(draw, (618, 294), "添加备注", LINE, TEXT)
    draw.text((484, 359), "确定性安全失败不可被人工覆盖", font=F16, fill=RED)


def scene_7(draw, p):
    draw_header(draw, 7, "质量达标，仍然可以阻断")
    rounded(draw, (45, 120, 915, 420), 22, PANEL, LINE)
    pill(draw, (72, 146), "RELEASE GATE", RED, TEXT)
    draw.text((72, 202), "BLOCKED", font=F50, fill=RED)
    draw.text((72, 270), "20 条必审样本尚未闭环", font=F24, fill=TEXT)
    checks = [
        ("高风险安全失败", "0", True),
        ("依据通过率", "100%", True),
        ("任务完成率", "98%", True),
        ("严重回归", "0", True),
        ("必审样本闭环", "30 / 50", False),
    ]
    for i, (label, value, ok) in enumerate(checks):
        y = 148 + i * 48
        x = 515
        color = LIME if ok else RED
        r = 9
        draw.ellipse((x, y + 2, x + r * 2, y + 2 + r * 2), fill=color)
        draw.text((x + 32, y), label, font=F16, fill=TEXT)
        draw.text((865, y), value, font=F16, fill=color, anchor="ra")
    draw.text((72, 343), "门禁不是漂亮结论，而是风险责任的最后一道检查。", font=F16, fill=MUTED)


def scene_8(draw, p):
    draw_header(draw, 8, "可运行、可测试、可复核")
    tech = [("FastAPI", "API 与运行编排"), ("SQLite", "结果与审核留痕"), ("React / TS", "质量运营工作台")]
    for i, (name, sub) in enumerate(tech):
        x = 42 + i * 302
        local = ease((p - i * 0.1) / 0.3)
        y = int(126 + (1 - local) * 40)
        rounded(draw, (x, y, x + 270, y + 112), 16, PANEL, [GREEN, CYAN, LIME][i])
        draw.text((x + 20, y + 20), name, font=F20, fill=TEXT)
        draw.text((x + 20, y + 61), sub, font=F14, fill=MUTED)
    rounded(draw, (42, 264, 920, 423), 18, PANEL, LINE)
    draw.text((68, 291), "验证证据", font=F20, fill=TEXT)
    items = ["10 项后端自动化测试通过", "前端类型检查与生产构建通过", "浏览器走通双版本评测 → 复核 → 门禁 → 报告"]
    for i, item in enumerate(items):
        y = 333 + i * 31
        draw.ellipse((70, y + 3, 84, y + 17), fill=LIME)
        draw.text((76, y + 10), "✓", font=F12, fill=BG, anchor="mm")
        draw.text((98, y), item, font=F16, fill=TEXT)
    pill(draw, (756, 288), "PASS", LIME)


def scene_9(draw, p):
    draw_header(draw, 9, "证据边界比漂亮数字更重要")
    rounded(draw, (45, 122, 915, 376), 22, PANEL, LINE)
    draw.text((72, 151), "本次已验证", font=F20, fill=LIME)
    verified = ["公开资料衍生的 50 条合成测试", "可运行 MVP 与完整质量闭环", "自动化测试、构建与浏览器验收"]
    for i, t in enumerate(verified):
        draw.text((74, 196 + i * 43), "✓", font=F18, fill=LIME)
        draw.text((107, 194 + i * 43), t, font=F16, fill=TEXT)
    draw.line((480, 145, 480, 350), fill=LINE, width=1)
    draw.text((520, 151), "当前未验证", font=F20, fill=AMBER)
    pending = ["企业生产数据与真实部署", "真实模型效果与真实调用成本", "开源贡献被采纳或比赛获奖"]
    for i, t in enumerate(pending):
        draw.text((520, 196 + i * 43), "—", font=F18, fill=AMBER)
        draw.text((551, 194 + i * 43), t, font=F16, fill=TEXT)
    draw.text((50, 413), "Agent QualityOps", font=F24, fill=TEXT)
    draw.text((275, 418), "让每一次发布，都有证据可复核。", font=F18, fill=LIME)


SCENE_RENDERERS = [scene_1, scene_2, scene_3, scene_4, scene_5, scene_6, scene_7, scene_8, scene_9]


def split_phrases(text: str):
    parts = [p.strip() for p in re.split(r"(?<=[。！？；])", text) if p.strip()]
    out = []
    for part in parts:
        while len(part) > 30:
            cut = 26
            comma = max(part.rfind("，", 0, 30), part.rfind("、", 0, 30))
            if comma >= 15:
                cut = comma + 1
            out.append(part[:cut])
            part = part[cut:]
        if part:
            out.append(part)
    return out


def subtitle_text_at(subs, t):
    for start, end, text in subs:
        if start <= t < end:
            return text
    return ""


def srt_time(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_timeline(manifest):
    starts, subs, cursor = [], [], 0.0
    srt_rows = []
    idx = 1
    for scene in manifest["scenes"]:
        starts.append(cursor)
        phrases = split_phrases(scene["text"])
        weights = [max(1, len(re.sub(r"\W", "", x))) for x in phrases]
        unit = scene["audio_duration"] / sum(weights)
        t = cursor + 0.8
        for phrase, weight in zip(phrases, weights):
            duration = unit * weight
            subs.append((t, t + duration, phrase))
            srt_rows.append(f"{idx}\n{srt_time(t)} --> {srt_time(t + duration)}\n{phrase}\n")
            idx += 1
            t += duration
        cursor += scene["scene_duration"]
    OUT_SRT.write_text("\n".join(srt_rows), encoding="utf-8")
    return starts, subs, cursor


def build_audio(manifest, starts, total_duration):
    total_samples = math.ceil(total_duration * SR)
    mix = np.zeros((total_samples, 2), dtype=np.float32)
    for scene, start in zip(manifest["scenes"], starts):
        samples, source_sr = sf.read(str(ROUND3 / scene["audio"]), dtype="float32", always_2d=True)
        mono = samples.mean(axis=1)
        if source_sr != SR:
            mono = resample_poly(mono, SR, source_sr).astype(np.float32)
        stereo = np.column_stack([mono, mono])
        offset = int((start + 0.8) * SR)
        end = min(total_samples, offset + len(stereo))
        mix[offset:end] += stereo[: end - offset]
    peak = float(np.abs(mix).max()) or 1.0
    mix *= min(0.93 / peak, 1.0)
    pcm = np.clip(mix * 32767, -32768, 32767).astype("<i2")
    with wave.open(str(OUT_WAV), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())
    return pcm


def draw_subtitle(img, text):
    if not text:
        return
    draw = ImageDraw.Draw(img)
    lines = wrap_text(draw, text, F18, 800)
    if len(lines) > 2:
        lines = lines[:2]
    line_h = 29
    box_h = 22 + len(lines) * line_h
    y0 = H - box_h - 13
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle((45, y0, 915, H - 12), radius=12, fill=(0, 0, 0, 205))
    for i, line in enumerate(lines):
        od.text((W // 2, y0 + 10 + i * line_h), line, font=F18, fill=(255, 255, 255, 255), anchor="ma")
    img.alpha_composite(overlay)


def render(manifest, starts, subs, total_duration, pcm):
    container = av.open(str(OUT_VIDEO), "w")
    video = container.add_stream("libx264", rate=FPS)
    video.width = W
    video.height = H
    video.pix_fmt = "yuv420p"
    video.options = {"crf": "23", "preset": "veryfast", "movflags": "+faststart"}
    audio = container.add_stream("aac", rate=SR)
    audio.layout = "stereo"
    audio.bit_rate = 128_000
    total_frames = math.ceil(total_duration * FPS)
    audio_cursor = 0
    audio_chunk = 1024

    for fi in range(total_frames):
        t = fi / FPS
        while audio_cursor / SR <= t and audio_cursor < len(pcm):
            block = pcm[audio_cursor : audio_cursor + audio_chunk]
            if len(block) < audio_chunk:
                block = np.pad(block, ((0, audio_chunk - len(block)), (0, 0)))
            planar = block.T.copy()
            af = av.AudioFrame.from_ndarray(planar, format="s16p", layout="stereo")
            af.sample_rate = SR
            af.pts = audio_cursor
            af.time_base = Fraction(1, SR)
            for packet in audio.encode(af):
                container.mux(packet)
            audio_cursor += audio_chunk

        scene_index = max(i for i, s in enumerate(starts) if s <= t)
        scene_start = starts[scene_index]
        scene_duration = manifest["scenes"][scene_index]["scene_duration"]
        p = (t - scene_start) / scene_duration
        img = base_image().convert("RGBA")
        draw = ImageDraw.Draw(img)
        SCENE_RENDERERS[scene_index](draw, p)
        # 场景开合淡入，避免硬切
        fade = min(1.0, (t - scene_start) / 0.35, (scene_start + scene_duration - t) / 0.35)
        if fade < 1:
            shade = Image.new("RGBA", img.size, (4, 12, 10, int(255 * (1 - max(0, fade)))))
            img.alpha_composite(shade)
        draw_subtitle(img, subtitle_text_at(subs, t))
        vf = av.VideoFrame.from_ndarray(np.asarray(img.convert("RGB")), format="rgb24")
        vf.pts = fi
        for packet in video.encode(vf):
            container.mux(packet)

        if fi % (FPS * 20) == 0:
            print(f"render {fi}/{total_frames} ({t:.1f}s)", flush=True)

    while audio_cursor < len(pcm):
        block = pcm[audio_cursor : audio_cursor + audio_chunk]
        if len(block) < audio_chunk:
            block = np.pad(block, ((0, audio_chunk - len(block)), (0, 0)))
        af = av.AudioFrame.from_ndarray(block.T.copy(), format="s16p", layout="stereo")
        af.sample_rate = SR
        af.pts = audio_cursor
        af.time_base = Fraction(1, SR)
        for packet in audio.encode(af):
            container.mux(packet)
        audio_cursor += audio_chunk
    for packet in video.encode():
        container.mux(packet)
    for packet in audio.encode():
        container.mux(packet)
    container.close()


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    starts, subs, total_duration = build_timeline(manifest)
    pcm = build_audio(manifest, starts, total_duration)
    render(manifest, starts, subs, total_duration, pcm)
    print(json.dumps({
        "video": str(OUT_VIDEO),
        "duration": round(total_duration, 3),
        "frames": math.ceil(total_duration * FPS),
        "srt": str(OUT_SRT),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
