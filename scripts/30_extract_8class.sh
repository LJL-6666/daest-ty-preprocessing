#!/bin/bash
# 9 类 + 问卷 → 8 类自评完整输入 pkl
# 输出: ${DAEST_PREP_ROOT}/output/8_movie_self/, ${DAEST_PREP_ROOT}/output/8_communication_self/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="${SCRIPT_DIR}/../src"

: "${DAEST_DATA_ROOT:?请设置 DAEST_DATA_ROOT，见 env/PATHS.md}"
: "${DAEST_PREP_ROOT:?请设置 DAEST_PREP_ROOT，见 env/PATHS.md}"

echo "=== 汇总：9 类 + 问卷 → 8 类自评 ==="

# 观影 8 类自评
python "${SRC_DIR}/extract_8class_movie_self.py"

# 讲述 8 类自评
python "${SRC_DIR}/extract_8class_communication_self.py"

echo ""
echo "=== 完成 ==="
ls -lh "${DAEST_PREP_ROOT}/output/8_movie_self/data_8class_movie_self.pkl" 2>/dev/null || echo "  ⚠ 8_movie_self 未生成"
ls -lh "${DAEST_PREP_ROOT}/output/8_communication_self/data_8class_communication_self.pkl" 2>/dev/null || echo "  ⚠ 8_communication_self 未生成"
