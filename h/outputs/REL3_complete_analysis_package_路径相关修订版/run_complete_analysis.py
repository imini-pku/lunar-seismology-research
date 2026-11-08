"""Run the complete REL3 waveform, terrain, observation, and report workflow."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REQUIRED_INPUTS = (
    Path(r"E:\project_releasy_flat_noscatter\output\station.nc"),
    Path(r"E:\project_releasy_flat_scatter\output\station.nc"),
    Path(r"E:\project_releasy_topo_noscatter\output\station.nc"),
    Path(r"E:\project_releasy_topo_scatter\output\station.nc"),
    Path(r"D:\software\CGFD3D_v26.03\revise\prep_medium\rel3_Z_300_1500_topo.txt"),
    Path(r"D:\software\CGFD3D_v26.03\revise\usefiles\16s.12.BHZ.txt"),
    Path(r"D:\software\CGFD3D_v26.03\revise\usefiles\16s.12.BHE.sac"),
    Path(r"D:\software\CGFD3D_v26.03\revise\usefiles\16s.12.BHN.sac"),
)

ANALYSIS_STEPS = (
    ("四模型波形、三条射线与真实S12图件", "plot_releasy_waveform_comparison.py"),
    ("波形—地形—散射基础因子分析", "analyze_releasy_relationships.py"),
    ("论文方法驱动的包络、Qc与稳健性分析", "analyze_releasy_literature_guided.py"),
    ("三分量ZRT与qP-qSV-SH分析", "analyze_three_component_psvsh.py"),
    ("三条射线传播路径地形分析", "generate_path_based_ray_analysis.py"),
    ("32条结论波形证据图册", "generate_conclusion_waveform_atlas.py"),
)


def validate_inputs() -> None:
    missing = [path for path in REQUIRED_INPUTS if not path.is_file()]
    if missing:
        formatted = "\n".join(f"- {path}" for path in missing)
        raise FileNotFoundError(f"缺少以下输入文件：\n{formatted}")
    missing_scripts = [
        SCRIPT_DIR / script_name
        for _, script_name in ANALYSIS_STEPS
        if not (SCRIPT_DIR / script_name).is_file()
    ]
    if missing_scripts:
        formatted = "\n".join(f"- {path}" for path in missing_scripts)
        raise FileNotFoundError(f"缺少以下分析脚本：\n{formatted}")


def run_script(label: str, script_name: str) -> None:
    print(f"\n=== {label} ===", flush=True)
    subprocess.run(
        [sys.executable, str(SCRIPT_DIR / script_name)],
        cwd=SCRIPT_DIR,
        check=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="一键重现REL3四模型、三分量、路径地形、32条图证结论和综合报告。"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="只检查输入文件和脚本，不执行计算。",
    )
    parser.add_argument(
        "--skip-document",
        action="store_true",
        help="完成数据分析和图件后，不生成Word综合报告。",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    validate_inputs()
    print("输入文件与脚本检查通过。", flush=True)
    if args.check_only:
        return
    for label, script_name in ANALYSIS_STEPS:
        run_script(label, script_name)
    if not args.skip_document:
        report_builder = SCRIPT_DIR / "build_complete_rel3_report.py"
        if not report_builder.is_file():
            raise FileNotFoundError(report_builder)
        run_script("完整中文Word报告与交付包", report_builder.name)
    print("\n全部步骤完成。", flush=True)


if __name__ == "__main__":
    main()
