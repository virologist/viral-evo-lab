#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_contracts.py —— 团队契约文本检查（V2 · 2026-10-14）
执行：扫描 agents/*.md 是否含关键契约条款（输入信封/工具白名单/纪律审判等）
边界：仅做"关键词存在性"确定性检查；不判断语义
返回：EXIT=0 全过；EXIT=5 缺条款
"""
import json
import re
import sys
from pathlib import Path

# 契约条款黑名单（仅团队契约——v1.2.3 体系；项目治理约束 R1-R9 不在此查）
# 设计：每条仅需命中 1 个关键词即过；主理人 MD 自身不需含"团队契约回指"段
# R2-5 重构（2026-10-15）：信封细节/纪律审判/知识态等全员同版内容已抽至
# references/team-contract.md（装配时注入），成员层只查"指针+自身专属三件"
CONTRACTS = {
    "回传信封指针": r"result_envelope|上行信封",
    "能力/禁止边界": r"能力边界|禁止边界",
    "路由判定表": r"路由判定表",
}

# 团队契约正本（全员同版）必含条款——成员层抽走的 4 类内容在此验收
TEAM_CONTRACT = {
    "信封 schema 完整": r"result_envelope|agent_id.*task_id.*phase.*status|6 必填字段",
    "status 自评准则": r"status自评准则|success.*partial.*failed",
    "纪律审判时点": r"纪律审判|T0.*派 spawn|T1.*收 envelope",
    "数字核验关卡": r"verify_numbers|verify_member_output|数字核验|未溯源",
    "知识态/真源": r"confirmed_hypotheses|knowledge_index|RESEARCH_OPS_DIR|知识态",
    "下行 task_payload": r"task_payload|下行",
    "两仓分层纪律": r"两仓分层|GOVERNANCE_BOUNDARIES|check_scope",
}

# B（2026-10-14）：skills 层契约（SKILL.md 唯一入口须索引团队工具+核心铁律）
SKILL_CONTRACTS = {
    "团队工具索引（scripts/ 全清单）": r"assemble_spawn_prompt|verify_member_output|check_scope|write_checklist|find_knowledge|validate_contracts",
    "数字必溯源铁律": r"数字必溯源|未溯源|待人工核验",
    "禁项目叙事铁律（P2）": r"禁项目叙事|GOVERNANCE_BOUNDARIES|check_scope",
    "契约源回指（主理人 MD）": r"team-lead|主理人",
}


def check_agent(agent_path: Path) -> list[dict]:
    """返回该 agent 缺失的契约条款列表。"""
    try:
        text = agent_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return [{"contract": "FILE_READ_ERROR", "missing_pattern": ""}]
    miss = []
    for name, pat in CONTRACTS.items():
        if not re.search(pat, text, re.M | re.I):
            miss.append({"contract": name, "missing_pattern": pat})
    return miss


def check_skill(skill_md: Path) -> list[dict]:
    """B（2026-10-14）：skills 层契约孤岛检查。
    SKILL.md 是成员任务型入口，须索引团队工具 + 两条铁律（数字溯源/禁项目叙事）。
    references/*.md 按需加载，不强检（避免过度扩散）。
    """
    try:
        text = skill_md.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return [{"contract": "FILE_READ_ERROR", "missing_pattern": ""}]
    miss = []
    for name, pat in SKILL_CONTRACTS.items():
        if not re.search(pat, text, re.M | re.I):
            miss.append({"contract": name, "missing_pattern": pat})
    return miss


def check_manifests(base: Path) -> list[dict]:
    """P2-⑩（2026-10-15）：双 manifest 版本一致性（今日曾 2 次不同步）。"""
    miss = []
    versions = {}
    for mf in (".codebuddy-plugin/plugin.json", ".claude-plugin/plugin.json"):
        p = base / mf
        try:
            versions[mf] = json.loads(p.read_text(encoding="utf-8")).get("version", "?")
        except (OSError, json.JSONDecodeError) as e:
            miss.append({"contract": f"{mf} 读取失败", "missing_pattern": str(e)})
    if len(set(versions.values())) > 1:
        miss.append({"contract": "双 manifest version 不一致",
                     "missing_pattern": str(versions)})
    return miss


def main() -> int:
    base = Path(__file__).resolve().parent.parent
    total_missing = 0

    # ⓪ 双 manifest 版本一致性
    for m in check_manifests(base):
        total_missing += 1
        print(f"❌ manifest: {m['contract']}（{m['missing_pattern']}）")

    # ① agents 层（9 员；主理人 MD 是契约源头，套成员层模式无意义）
    for ag in sorted((base / "agents").glob("*.md")):
        if ag.name == "viral-evo-lab-team-lead.md":
            print("✅ agents/viral-evo-lab-team-lead.md（契约源头，豁免成员层检查）")
            continue
        miss = check_agent(ag)
        if miss:
            total_missing += len(miss)
            print(f"❌ agents/{ag.name}: 缺 {len(miss)} 项契约条款")
            for m in miss[:2]:
                print(f"   - {m['contract']}（需匹配: /{m['missing_pattern'][:40]}/）")
        else:
            print(f"✅ agents/{ag.name}")

    # ② skills 层（viral-evo-core/SKILL.md 唯一入口）
    skill_md = base / "skills/viral-evo-core/SKILL.md"
    if skill_md.is_file():
        miss = check_skill(skill_md)
        if miss:
            total_missing += len(miss)
            print(f"❌ skills/SKILL.md: 缺 {len(miss)} 项契约条款")
            for m in miss[:2]:
                print(f"   - {m['contract']}（需匹配: /{m['missing_pattern'][:40]}/）")
        else:
            print(f"✅ skills/SKILL.md（工具索引+铁律完整）")

    # ③ 团队契约正本（R2-5：成员层抽走的全员同版内容在此验收）
    tc = base / "skills/viral-evo-core/references/team-contract.md"
    if tc.is_file():
        tct = tc.read_text(encoding="utf-8")
        miss = []
        for name, pat in TEAM_CONTRACT.items():
            if not re.search(pat, tct, re.M | re.I):
                miss.append({"contract": name, "missing_pattern": pat})
        if miss:
            total_missing += len(miss)
            print(f"❌ skills/team-contract.md: 缺 {len(miss)} 项正本条款")
            for m in miss[:2]:
                print(f"   - {m['contract']}（需匹配: /{m['missing_pattern'][:40]}/）")
        else:
            print("✅ skills/team-contract.md（正本 7 条款完整）")

    if total_missing:
        print(f"\n总计 {total_missing} 处契约缺失——影响层间一致性，建议补齐")
        return 5
    print("\n✅ 全员契约完整（manifest 一致 + agents 9 + SKILL + 契约正本）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
