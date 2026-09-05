#!/bin/bash
# 逐被试 pkl → 9 类完整输入 pkl
# 输出: ${DAEST_PREP_ROOT}/output/9_movie/, ${DAEST_PREP_ROOT}/output/9_communication/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="${SCRIPT_DIR}/../src"

: "${DAEST_PREP_ROOT:?请设置 DAEST_PREP_ROOT，见 env/PATHS.md}"

echo "=== 汇总：逐被试 → 9 类 ==="

# 观影 9 类
python "${SRC_DIR}/extract_9class_movie.py"

# 讲述 9 类
python "${SRC_DIR}/extract_9class_communication.py"

echo ""
echo "=== 完成 ==="
ls -lh "${DAEST_PREP_ROOT}/output/9_movie/data_9class_movie.pkl" 2>/dev/null || echo "  ⚠ 9_movie 未生成"
ls -lh "${DAEST_PREP_ROOT}/output/9_communication/data_9class_communication.pkl" 2>/dev/null || echo "  ⚠ 9_communication 未生成"
