#!/bin/bash
# 原始脑电 → 逐被试 pkl（0.05–47 Hz 滤波 + ICA + 降采样 250 Hz）
# 输出: ${DAEST_PREP_ROOT}/output/movie/*.pkl, ${DAEST_PREP_ROOT}/output/communication/*.pkl
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="${SCRIPT_DIR}/../src"

: "${DAEST_DATA_ROOT:?请设置 DAEST_DATA_ROOT，见 env/PATHS.md}"
: "${DAEST_PREP_ROOT:?请设置 DAEST_PREP_ROOT，见 env/PATHS.md}"

echo "=== 预处理：原始脑电 → 逐被试 pkl ==="
echo "  输入: ${DAEST_DATA_ROOT}/data-tongyong/原始数据/脑电近红外/标准脑电"
echo "  输出: ${DAEST_PREP_ROOT}/output/"
echo ""

# 观影任务
python "${SRC_DIR}/main_tongyong.py" --task-type movie --clisa-or-not no

# 讲述任务
python "${SRC_DIR}/main_tongyong.py" --task-type communication --clisa-or-not no

echo ""
echo "=== 完成 ==="
echo "  观影: $(ls "${DAEST_PREP_ROOT}/output/movie/"*.pkl 2>/dev/null | wc -l) 个被试"
echo "  讲述: $(ls "${DAEST_PREP_ROOT}/output/communication/"*.pkl 2>/dev/null | wc -l) 个被试"
