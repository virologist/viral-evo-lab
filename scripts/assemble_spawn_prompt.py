#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
成员 spawn 人设装配器（viral-evo-lab 定制版 = shared-core 公共版 + V1 增量）
==========================================================================
⚠ 来源声明（v3.4.1 R9，2026-10-14）：
    本文件 = shared-core 公共版（plugins/shared-core/assemble_spawn_prompt.py，369 行）
    + 本包 V1 增量（约 105 行：git tag 版本探测 _detect_team_version /
    V1 关键数字模式 _V1_PATTERNS / _v1_extract / spawn 前自动核验 _auto_verify_payload）。
    其余 4 个无差异包已改为 shim 转调 shared-core；本包因有实质增量，**独立维护**。
    同步纪律：shared-core 公共逻辑演进时，须评估本包是否需要跟进（diff 公共版与本文件，
    公共段变更按需合并；V1 增量段保持私有）。合并记录写 CHANGELOG。
    当前基线：shared-core 公共版 369 行（2026-10-14 下沉时快照）。

用途（公共能力）：把「成员 MD 人设 + 技能资源绝对路径 + task_payload + 输出契约」确定性地
拼装成一份可直接作为 Agent 工具 prompt 的 spawn 文案，供主理人下发。

为什么要这个脚本：
    WorkBuddy 平台在 TeamCreate + Agent(name=成员ID) 时**不会**自动把
    agents/<member>.md 注入被 spawn 的 teammate（实测：团队配置文件中
    agentType=general-purpose，prompt 仅含主理人下发内容）。
    因此「成员专业产出」必须由主理人显式注入人设。手工复制 MD 易漏、易旧，
    交给脚本做确定性装配 + 白名单校验。

边界（严格守）：
    本脚本只做「结构拼装 / 路径解析 / 白名单校验」这类确定性工作；
    「派谁 / 任务怎么写 / 产出是否合格」仍是 LLM 与人的判断，脚本不介入。

用法：
    # 1. 只装配人设骨架（主理人自己补任务段）
    python3 assemble_spawn_prompt.py --member contradiction-analyst

    # 2. 装配人设 + 任务段（推荐，一次成型）
    python3 assemble_spawn_prompt.py --member contradiction-analyst \
        --phase 2 --task-id T-20260929-001 --task-file /tmp/phase2_task.md

    # 3. 同时校验任务包四要素是否齐全
    python3 assemble_spawn_prompt.py --member contradiction-analyst \
        --task-file /tmp/phase2_task.md --check-task-package

    # 4. 列出本团队全部合法成员 ID（路由白名单）
    python3 assemble_spawn_prompt.py --list-members

    # 5. 写到文件（长 prompt 建议落盘后再由主理人粘贴/引用）
    python3 assemble_spawn_prompt.py --member contradiction-analyst --out /tmp/spawn.md

退出码：
    0 = 成功；2 = 成员 ID 不在白名单；3 = 文件缺失；4 = 任务包要素缺失
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------- 常量

LOG_PREFIX = "[assemble_spawn_prompt]"

# 任务包四要素（Anthropic 委派协议；缺一即补齐再 spawn）
TASK_PACKAGE_FIELDS = ["objective", "output_format", "constraints", "task_boundary"]


def log(msg: str) -> None:
    """统一日志输出到 stderr，避免污染 stdout 的 prompt 正文。"""
    print(f"{LOG_PREFIX} {msg}", file=sys.stderr)


def _detect_team_version(expert_dir: Path) -> str | None:
    """从 git tag 探测最近 v* 版本号（v1.2.2 → '1.2.2'）；失败返回 None。"""
    try:
        import subprocess
        r = subprocess.run(
            ["git", "-C", str(expert_dir), "tag", "--list", "v*", "--sort=-creatordate"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode != 0:
            return None
        tags = [t for t in r.stdout.strip().splitlines() if t.startswith("v")]
        if not tags:
            return None
        return tags[0].lstrip("v")
    except (OSError, subprocess.TimeoutExpired, FileNotFoundError):
        return None


# V1 关键数字模式（与 verify_numbers.py 对齐；避免循环 import，直接内联）
_V1_PATTERNS = [
    ("pct",    re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%")),
    ("n_eq",   re.compile(r"\bn\s*=\s*(\d{2,6})\b", re.I)),
    ("p_val",  re.compile(r"\bp\s*=\s*(0\.\d+|\d\.\d+e-?\d+|\d\.\d+)", re.I)),
    ("dprime", re.compile(r"D[\u2032\u2035]\s*=\s*([+-]?\d\.\d+)")),
    ("ci",     re.compile(r"CI\s*[\[（(]\s*([+-]?\d\.\d+)\s*,\s*([+-]?\d\.\d+)\s*[\]）)]")),
]
_V1_EXCLUDE_YEAR = re.compile(r"^20[0-2]\d$")
_V1_EXCLUDE_VERSION = re.compile(r"^[vV]\d+(\.\d+){1,2}$|^\d+\.\d+\.\d+$")


def _v1_extract(payload: str) -> list[tuple[str, str]]:
    """从 task_payload 文本提取关键数字（与 verify_numbers.py 同口径）。"""
    out, seen = [], set()
    for kind, pat in _V1_PATTERNS:
        for m in pat.finditer(payload):
            vals = list(m.groups())
            if kind == "ci":
                # CI 区间取两端
                vals = [vals[0], vals[1]]
            else:
                vals = [vals[0]]
            for v in vals:
                if not v or _V1_EXCLUDE_YEAR.match(v) or _V1_EXCLUDE_VERSION.match(v):
                    continue
                key = (kind, v)
                if key in seen:
                    continue
                seen.add(key); out.append((kind, v))
    return out


def _auto_verify_payload(expert_dir: Path, payload: str, research_ops: str) -> dict:
    """
    V1：spawn 前自动核验 task_payload 中的关键数字。
    权威源：context_stack/confirmed_hypotheses.json 引用的 CSV/JSON 目录（由 RESEARCH_OPS_DIR 推）。
    缺失/未设置 → 静默跳过（不阻塞 spawn，记 stderr）。
    """
    if not research_ops:
        log("V1 跳过：未设 RESEARCH_OPS_DIR，task_payload 数字未自动核验")
        return {"unverified": [], "warning_text": None, "skipped": True}
    # 权威源默认 = research-ops 的 M*/output 目录；若不存在则用 research-ops 全仓
    sources = []
    ctx = Path(research_ops) / "context_stack"
    for sub in ("outputs", "data", "results"):
        d = ctx / sub
        if d.is_dir():
            sources.append(str(d))
    # 也尝试找 research-ops 下任何含 csv/json 的子目录
    if not sources:
        for d in sorted(Path(research_ops).rglob("output*")):
            if d.is_dir() and d.suffix == "":
                sources.append(str(d))
    if not sources:
        log(f"V1 跳过：未找到权威源目录（{research_ops} 下无 outputs/data/results）")
        return {"unverified": [], "warning_text": None, "skipped": True}

    # 复用 verify_numbers.py 的提取与匹配逻辑
    nums = _v1_extract(payload)
    if not nums:
        return {"unverified": [], "warning_text": None}
    # 加载权威源池
    pool_chunks = []
    for sp in sources:
        pth = Path(sp)
        if pth.is_dir():
            for f in sorted(pth.rglob("*")):
                if f.suffix.lower() in (".csv", ".json") and f.is_file():
                    try:
                        pool_chunks.append(f.read_text(encoding="utf-8", errors="ignore"))
                    except OSError:
                        pass
    pool = "\n".join(pool_chunks)
    unverified = []
    for kind, val in nums:
        cands = {val}
        try:
            f = float(val)
            cands |= {f"{f:.2f}", f"{f:.3f}", f"{f:.4f}"} if f >= 1 else {f"{f:.3f}", f"{f:.4f}", f"{f:.5f}"}
        except ValueError:
            pass
        if not any(c in pool for c in cands):
            unverified.append({"kind": kind, "value": val})
    return {"unverified": unverified, "warning_text": None, "skipped": False}


# ---------------------------------------------------------------- 路径与元数据

def resolve_expert_dir(explicit: str | None) -> Path:
    """
    解析专家包根目录。
    优先级：命令行显式传入 > 脚本文件位置反推（scripts/ 的上两级）> 环境变量。
    禁止猜测：三者都拿不到就报错退出，绝不用相对路径硬编码。
    """
    if explicit:
        p = Path(explicit).expanduser().resolve()
        if not p.is_dir():
            log(f"❌ 传入的专家包目录不存在：{p}")
            sys.exit(3)
        return p

    env = os.environ.get("EXPERT_DIR")
    if env:
        p = Path(env).expanduser().resolve()
        if p.is_dir():
            return p
        log(f"⚠️ 环境变量 EXPERT_DIR 指向的目录不存在，回退脚本位置反推：{env}")

    inferred = Path(__file__).resolve().parent.parent
    if (inferred / "agents").is_dir():
        return inferred

    log("❌ 无法解析专家包目录。请用 --expert-dir 显式传入。")
    sys.exit(3)


def load_plugin(expert_dir: Path) -> dict:
    """读取 plugin.json（权威元数据：成员白名单、技能清单）。"""
    candidates = [
        expert_dir / ".codebuddy-plugin" / "plugin.json",
        expert_dir / ".claude-plugin" / "plugin.json",
        expert_dir / "plugin.json",
    ]
    for c in candidates:
        if c.is_file():
            try:
                return json.loads(c.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                log(f"❌ plugin.json 解析失败：{c} -> {e}")
                sys.exit(3)
    log(f"❌ 未找到 plugin.json， searched: {[str(c) for c in candidates]}")
    sys.exit(3)


def load_member_ids(plugin: dict) -> list[str]:
    """从 plugin.json 提取成员白名单（teamInfo.memberAgents 优先，回退 members）。"""
    team_info = plugin.get("teamInfo") or {}
    ids = list(team_info.get("memberAgents") or [])
    if not ids:
        ids = [m.get("id") for m in plugin.get("members", []) if m.get("id")]
    return [i for i in ids if i]


# ---------------------------------------------------------------- 成员 MD 解析

def load_member_md(expert_dir: Path, member_id: str) -> str:
    """读取成员 MD 全文（人设注入的主体）。"""
    md = expert_dir / "agents" / f"{member_id}.md"
    if not md.is_file():
        log(f"❌ 成员 MD 不存在：{md}")
        sys.exit(3)
    return md.read_text(encoding="utf-8")


def parse_frontmatter(md_text: str) -> tuple[dict, str]:
    """
    拆分 frontmatter 与正文。
    返回 (frontmatter_dict, body)。解析失败时 frontmatter 为空字典（不阻断）。
    """
    if not md_text.startswith("---"):
        return {}, md_text
    parts = md_text.split("---", 2)
    if len(parts) < 3:
        return {}, md_text
    fm_raw, body = parts[1], parts[2]
    fm = {}
    # 极简 YAML 解析：只取本脚本关心的 key（name/skills/maxTurns/profession/displayName）
    for key in ("name", "maxTurns"):
        m = re.search(rf"^{key}:\s*(.+)$", fm_raw, re.M)
        if m:
            fm[key] = m.group(1).strip().strip('"')
    m = re.search(r"^skills:\s*\[(.+?)\]", fm_raw, re.M)
    if m:
        fm["skills"] = [s.strip().strip('"') for s in m.group(1).split(",")]
    return fm, body.lstrip("\n")


def resolve_skill_paths(expert_dir: Path, skills: list[str] | None) -> list[str]:
    """
    把 skills 名称解析为 references/skill 的绝对路径清单。
    只做路径解析（确定性），不做「该不该加载」的语义判断——那归成员自己按需。
    """
    if not skills:
        return []
    paths: list[str] = []
    for sk in skills:
        # 技能目录可能在 skills/<name>/ 下
        base = expert_dir / "skills" / sk
        if base.is_dir():
            paths.append(str(base / "SKILL.md"))
            ref_dir = base / "references"
            if ref_dir.is_dir():
                for f in sorted(ref_dir.rglob("*.md")):
                    paths.append(str(f))
        else:
            # 退化为 skills 根目录同级扫描（兼容扁平布局）
            for f in sorted((expert_dir / "skills").rglob(f"{sk}.md")):
                paths.append(str(f))
    # 去重保序
    seen, out = set(), []
    for p in paths:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def resolve_shared_refs(expert_dir: Path) -> list[str]:
    """收集专家包级共享资源（references/ config/ scripts/），供成员按需取用。"""
    out: list[str] = []
    for sub in ("references", "config"):
        d = expert_dir / sub
        if d.is_dir():
            for f in sorted(d.rglob("*")):
                if f.is_file() and f.suffix in (".md", ".yaml", ".yml", ".json"):
                    out.append(str(f))
    s = expert_dir / "scripts"
    if s.is_dir():
        for f in sorted(s.glob("*.py")):
            out.append(str(f))
    return out


# ---------------------------------------------------------------- 任务包校验

def check_task_package(task_text: str) -> tuple[bool, list[str]]:
    """
    校验任务包四要素是否齐全（objective / output_format / constraints / task_boundary）。
    这是**结构性校验**（字段存在性），属确定性范畴；内容质量由主理人判断。
    """
    low = task_text.lower()
    missing = [f for f in TASK_PACKAGE_FIELDS if f not in low]
    return (not missing), missing


# ---------------------------------------------------------------- 装配

def assemble(expert_dir: Path, member_id: str, fm: dict, body: str,
             task_text: str | None, phase: int | None,
             task_id: str | None, run_dir: str | None,
             member_ids: list[str] | None = None,
             research_ops: str = "") -> str:
    """拼装最终 spawn prompt。结构固定，便于审计与 diff。"""
    skills = fm.get("skills") or []
    skill_paths = resolve_skill_paths(expert_dir, skills)
    shared = resolve_shared_refs(expert_dir)
    if not research_ops:
        research_ops = os.environ.get("RESEARCH_OPS_DIR", "")

    # ---- 团队版本号（E1 · 2026-10-21）：从 git tag 探测最近含 v* 的 tag ----
    team_ver = _detect_team_version(expert_dir)

    # ---- V1（2026-10-21）：spawn 前自动核验 task_payload 关键数字 ----
    # 边界：仅做数字存在性核对（确定性 grep），不判断数字合理性
    if task_text and os.environ.get("VERIFY_NUMBERS_AUTO", "1") != "0":
        payload_verdict = _auto_verify_payload(expert_dir, task_text, research_ops)
        if payload_verdict["unverified"]:
            log(f"⚠️  V1 警告：task_payload 含 {len(payload_verdict['unverified'])} 个未溯源数字：")
            for u in payload_verdict["unverified"][:5]:
                log(f"    {u['kind']}: {u['value']}")
            log(f"  处置：spawn 仍继续（确定性 grep ≠ 语义判断），但主理人必须显式 ACK 或修改 task_payload")
            # 写入 spawn prompt 头部 + checklist hint（避免 f-string 嵌套反斜杠）
            sample = ", ".join(
                f"{u['kind']}:{u['value']}"
                for u in payload_verdict["unverified"][:3]
            )
            payload_verdict["warning_text"] = (
                f"⚠️ V1 自动核验：task_payload 含 {len(payload_verdict['unverified'])} 个未溯源数字"
                f"（{sample} 等）— 成员须把这些数字标 [待人工核验] 或在权威源中找到证据后重传"
            )
        else:
            payload_verdict["warning_text"] = None
    else:
        payload_verdict = {"unverified": [], "warning_text": None}

    lines: list[str] = []
    if team_ver:
        lines.append(f"【团队规范版本】v{team_ver}（本 prompt 据此版本装配；若你读到本行为过时规范，请上报主理人）")
        lines.append("")
    if payload_verdict.get("warning_text"):
        lines.append(payload_verdict["warning_text"])
        lines.append("")
    lines.append(f"你是下面这份角色定义所描述的专家。请完整代入该角色，严格遵守其输出规范与接口契约。")
    lines.append("")
    lines.append("=" * 20 + " 角色定义（专家包成员 MD 全文） " + "=" * 20)
    lines.append(f"---\nname: {fm.get('name', member_id)}")
    if skills:
        lines.append(f"skills: [{', '.join(skills)}]")
    if fm.get("maxTurns"):
        lines.append(f"maxTurns: {fm['maxTurns']}")
    lines.append("---")
    lines.append("")
    lines.append(body.rstrip())
    lines.append("=" * 20 + " 角色定义结束 " + "=" * 20)
    lines.append("")

    lines.append("【专家包资源绝对路径】（按需 Read，禁止猜测路径）")
    for p in skill_paths:
        lines.append(f"- {p}")
    for p in shared:
        lines.append(f"- {p}")
    lines.append("")

    # ---- R11（2026-10-14）：项目知识态注入（活跃/废弃假说 + 知识地图）----
    # 目的：spawn 时刻拦截"引用已废弃结论/幻觉数字"（A156T 事故根治点）。
    # 缺失时静默跳过（不阻塞装配），但打印 stderr 提醒。
    research_ops = os.environ.get("RESEARCH_OPS_DIR", "")
    if research_ops:
        hyp = Path(research_ops) / "context_stack/confirmed_hypotheses.json"
        kidx = Path(research_ops) / "context_stack/knowledge_index.md"
        inj: list[str] = []
        if hyp.is_file():
            try:
                d = json.loads(hyp.read_text(encoding="utf-8"))
                active = [h.get("id") for h in d.get("active_hypotheses", [])
                          if h.get("status") != "deprecated"]
                deprec = [h.get("id") for h in d.get("active_hypotheses", [])
                          if h.get("status") == "deprecated"]
                inj.append("【项目知识态·硬约束】（引用结论前必查；违反=虚报）")
                inj.append(f"- 活跃假说（可引用）：{', '.join(x or '?' for x in active) or '（无）'}")
                inj.append(f"- 已废弃假说（🔴禁止引用为当前结论，只能作历史陈述）："
                           f"{', '.join(x or '?' for x in deprec) or '（无）'}")
                inj.append(f"- 权威源：{hyp}")
                inj.append("- 任务产出中的关键数字（n=/百分比/p=/D′值）必须能在权威源 CSV 中 grep 到；"
                           "找不到 = 标注[待人工核验]，禁止直接当作事实陈述")
            except (OSError, json.JSONDecodeError) as e:
                log(f"confirmed_hypotheses.json 解析失败，跳过注入：{e}")
        if kidx.is_file():
            inj.append(f"- 知识地图（结论→证据链→文件路径）：{kidx}")
        if inj:
            lines.extend(inj)
            lines.append("")
    else:
        log("未设置 RESEARCH_OPS_DIR，跳过知识态注入（建议：export RESEARCH_OPS_DIR=<research-ops 绝对路径>）")

    if task_id or phase is not None:
        lines.append("【任务标识】")
        if task_id:
            lines.append(f"- task_id: {task_id}")
        if phase is not None:
            lines.append(f"- phase: {phase}")
        lines.append("")

    if task_text:
        lines.append("=" * 20 + " 任务包（task_payload） " + "=" * 20)
        lines.append(task_text.strip())
        lines.append("=" * 20 + " 任务包结束 " + "=" * 20)
        lines.append("")
    else:
        lines.append("【任务包】（主理人请在下方补全四要素后下发）")
        lines.append("- objective: <一句话目标>")
        lines.append("- output_format: <输出结构 + 回传 schema>")
        lines.append("- constraints: [<边界与红线>]")
        lines.append("- task_boundary: <做什么/不做什么/输入是什么>")
        lines.append("")

    # 合法下游白名单：防止成员在 next_agent_hint 里编造不存在的成员
    # （实测出现成员建议 solution-architect / prior-art / ip-strategist 等本团没有的角色）
    lines.append("【本团合法成员白名单】（next_agent_hint 只能从这里取值，禁止自创成员名）")
    for m in member_ids:
        mark = " ← 你" if m == member_id else ""
        lines.append(f"- {m}{mark}")
    lines.append("")

    lines.append("【推荐工具白名单】（本团成员惯例用法，仅供参考）")
    lines.append("- Read / Write / Edit: 读写文件（Write 受 run_dir 限制）")
    lines.append("- Bash: 跑脚本/查文件/执行命令（每个工具的实际调用频次由成员自决，无强制统计）")
    lines.append("- WebSearch / WebFetch: 外部检索（literature-scout 主用）")
    lines.append("- Agent: 派子任务（harness 团队场景）")
    lines.append("")
    lines.append("【回传要求·双通道】")
    if run_dir:
        artifact = f"{run_dir}/{task_id or 'T-UNKNOWN'}__{member_id}.md"
        lines.append(f"通道1（主·必须）：把完整产出写入文件 `{artifact}`。"
                     f"优先用 Write 工具；若无 Write 权限，改用 Bash heredoc "
                     f"（`cat > \"{artifact}\" << 'ARTEOF' ... ARTEOF`）。"
                     f"这是主理人读取产出的可靠通道。")
        lines.append("通道2（辅）：写完后用 SendMessage 给 team-lead 回传「一句话摘要 + 上述文件绝对路径」。")
        lines.append("⚠️ 严禁只 SendMessage 不落盘：实测中仅靠消息回传存在丢失风险，"
                     "主理人将按文件为准；文件缺失视为该成员本轮未交付。")
    else:
        lines.append("完成后用 SendMessage 把完整产出回传给 team-lead；"
                     "回传正文最前必须附上你角色定义中规定的上行信封 JSON。")
        lines.append("（提示：建议主理人用 --run-dir 启用落盘契约，回传更可靠）")
    return "\n".join(lines)


# ---------------------------------------------------------------- CLI

def _autodetect_research_ops() -> str:
    """C1（2026-10-21）：自动探测 research-ops 路径（取代裸环境变量依赖）
    探测顺序：env > CWD/research-ops > 专家包同级 research-ops > 静默跳过
    """
    env_v = os.environ.get("RESEARCH_OPS_DIR", "").strip()
    if env_v and Path(env_v).is_dir():
        return env_v
    cwd_ro = Path.cwd() / "research-ops"
    if cwd_ro.is_dir():
        return str(cwd_ro.resolve())
    expert_parent = Path(__file__).resolve().parent.parent.parent
    sibling = expert_parent / "research-ops"
    if sibling.is_dir():
        return str(sibling.resolve())
    return ""


def main() -> int:
    ap = argparse.ArgumentParser(
        description="成员 spawn 人设装配器：把成员 MD + 技能路径 + task_payload 拼成 spawn prompt")
    ap.add_argument("--expert-dir", default=None,
                    help="专家包根目录（默认：本脚本位置反推）")
    ap.add_argument("--member", help="成员 Agent ID（MD 文件名，不含 .md）")
    ap.add_argument("--task-file", help="任务包文本文件路径（推荐）")
    ap.add_argument("--phase", type=int, help="阶段号")
    ap.add_argument("--task-id", help="任务 ID，如 T-20260929-001")
    ap.add_argument("--out", help="输出到文件（默认 stdout）")
    ap.add_argument("--no-autodetect", action="store_true",
                    help="禁用 RESEARCH_OPS_DIR 自动探测（C1）")
    ap.add_argument("--check-task-package", action="store_true",
                    help="校验任务包四要素齐全，缺则 exit 4")
    ap.add_argument("--run-dir", default=None,
                    help="本轮运行目录；传入后会在 prompt 中注入「产出落盘契约」"
                         "（成员必须把产出写入 <run-dir>/<task_id>__<member-id>.md）")
    ap.add_argument("--list-members", action="store_true",
                    help="列出白名单成员 ID 后退出")
    args = ap.parse_args()

    expert_dir = resolve_expert_dir(args.expert_dir)
    plugin = load_plugin(expert_dir)
    member_ids = load_member_ids(plugin)
    # C1：自动探测 RESEARCH_OPS_DIR（除非禁用）
    if not args.no_autodetect and not os.environ.get("RESEARCH_OPS_DIR"):
        auto = _autodetect_research_ops()
        if auto:
            os.environ["RESEARCH_OPS_DIR"] = auto
            log(f"✅ C1 自动探测 RESEARCH_OPS_DIR = {auto}")

    if args.list_members:
        print("\n".join(member_ids))
        return 0

    if not args.member:
        log("❌ 缺少 --member（或用 --list-members 查看白名单）")
        return 3

    # 确定性路由白名单校验：非法成员 ID 直接拒绝，不进入 spawn
    if args.member not in member_ids:
        log(f"❌ 成员 ID 不在白名单：{args.member}")
        log(f"   白名单（来自 plugin.json teamInfo.memberAgents）：{member_ids}")
        return 2

    md_text = load_member_md(expert_dir, args.member)
    fm, body = parse_frontmatter(md_text)

    task_text = None
    if args.task_file:
        tf = Path(args.task_file).expanduser()
        if not tf.is_file():
            log(f"❌ 任务包文件不存在：{tf}")
            return 3
        task_text = tf.read_text(encoding="utf-8")

        if args.check_task_package:
            ok, missing = check_task_package(task_text)
            if not ok:
                log(f"❌ 任务包缺要素：{missing}（四要素：{TASK_PACKAGE_FIELDS}）")
                return 4
            log(f"✅ 任务包四要素齐全")

    run_dir = None
    if args.run_dir:
        rd = Path(args.run_dir).expanduser().resolve()
        rd.mkdir(parents=True, exist_ok=True)   # 幂等建目录，成员只需写文件
        run_dir = str(rd)
        log(f"✅ 运行目录就绪：{run_dir}")

    prompt = assemble(expert_dir, args.member, fm, body,
                      task_text, args.phase, args.task_id, run_dir, member_ids,
                      research_ops=os.environ.get("RESEARCH_OPS_DIR", ""))

    if args.out:
        Path(args.out).expanduser().write_text(prompt, encoding="utf-8")
        log(f"✅ 已写入：{args.out}（{len(prompt)} 字符）")
    else:
        print(prompt)

    log(f"✅ 装配完成：member={args.member} | expert_dir={expert_dir} "
        f"| skills={fm.get('skills') or []}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
