# DAEST · TY 情绪解码 · 预处理

TY 数据集 EEG 预处理流水线：原始脑电 → 建模可用 pkl。

与建模仓库 [`daest-ty-mainline`](https://github.com/LJL-6666/daest-ty-mainline) 联动。

## 产出

| pkl | 被试数 | 标签 | 大小 |
|---|---|---|---|
| `data_9class_movie.pkl` | 52 | 素材 9 类 | 2.6 GB |
| `data_9class_communication.pkl` | 118 | 素材 9 类 | 5.8 GB |
| `data_8class_movie_self.pkl` | 52 | 自评 8 类 | 2.6 GB |
| `data_8class_communication_self.pkl` | 118 | 自评 8 类 | 5.8 GB |

口径：250 Hz · 31 通道 · 28 视频 × 30 秒 · 0.05–47 Hz 滤波。

## 目录

```
src/        6 个核心脚本（预处理 + 汇总）
scripts/    3 个入口：00 验环境 → 10 预处理 → 20 9类 → 30 8类自评
data/       问卷 CSV（497 个文件，3.7 MB）
results/    QC 摘要、跳过记录
docs/       数据口径、与建模仓库衔接、预处理限制
MANIFEST/   大文件清单、原始数据来源
```

## 复现

```bash
# 1. 设置环境变量
export DAEST_DATA_ROOT=/path/to/TY/data
export DAEST_PREP_ROOT=/path/to/daest-ty-preprocessing

# 2. 验环境
bash scripts/00_check_env.sh

# 3. 预处理（原始脑电 → 逐被试 pkl）
bash scripts/10_run_preprocessing.sh

# 4. 汇总 9 类
bash scripts/20_extract_9class.sh

# 5. 汇总 8 类自评（需问卷）
bash scripts/30_extract_8class.sh
```

## 与建模仓库的衔接

建模仓库的 `src/cfgs/data/*.yaml` 通过 `${oc.env:DAEST_PREP_ROOT}` 引用本仓库产出的 pkl。
详见 [`docs/02_与建模仓库的衔接.md`](docs/02_与建模仓库的衔接.md)。

## 限制

见 [`docs/03_预处理限制.md`](docs/03_预处理限制.md)。
