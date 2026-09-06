# DAEST · TY 情绪解码 · 预处理

TY 与 FACED 数据集 EEG 预处理流水线：原始脑电 → 建模可用 pkl / mat。

与建模仓库 [`daest-ty-mainline`](https://github.com/LJL-6666/daest-ty-mainline) 联动。

## 产出

### TY 数据集

| pkl | 被试数 | 标签 | 大小 |
|---|---|---|---|
| `data_9class_movie.pkl` | 52 | 素材 9 类 | 2.6 GB |
| `data_9class_communication.pkl` | 118 | 素材 9 类 | 5.8 GB |
| `data_8class_movie_self.pkl` | 52 | 自评 8 类 | 2.6 GB |
| `data_8class_communication_self.pkl` | 118 | 自评 8 类 | 5.8 GB |

口径：250 Hz · 31 通道 · 28 视频 × 30 秒 · 0.05–47 Hz 滤波。

### FACED 数据集

| 输出 | 说明 |
|---|---|
| `0.05–47 Hz_mat/processed_data/*.mat` | 每被试一个 .mat，供建模仓库 `FACED_05_47` 配置使用 |

口径：250 Hz · 32 通道 · 28 视频 × 30 秒 · 0.05–47 Hz 滤波。

## 目录

```
src/        9 个核心脚本（TY 预处理 + FACED 预处理 + 汇总）
scripts/    4 个入口：00 验环境 → 10 TY 预处理 → 20 TY 9类 → 30 TY 8类自评 → 40 FACED
data/       行为与问卷数据：3 名被试样例 + 列定义说明（完整数据依申请获取，见 data/README.md）
results/    QC 摘要、跳过记录
docs/       数据口径、与建模仓库衔接、预处理限制
MANIFEST/   大文件清单、原始数据来源
```

## 数据

仓库内**不含完整的行为与问卷数据**。`data/example_questionnaire/` 只放了 3 名被试的
脱敏样例，用于说明文件格式与 `videoIndex` 对齐逻辑；完整的 129 名被试数据依申请获取。

- 列定义、缺失值约定、获取方式：[`data/README.md`](data/README.md)
- 数据许可为 CC BY 4.0（[`data/LICENSE`](data/LICENSE)），与代码的 MIT 许可**不同**

预处理流程本身读取的是 `DAEST_DATA_ROOT` 指向的原始数据目录，不依赖 `data/` 下的副本。

## 复现

```bash
# 1. 设置环境变量
export DAEST_DATA_ROOT=/path/to/TY/data
export DAEST_PREP_ROOT=/path/to/daest-ty-preprocessing
export EEGLAB_DIR=/path/to/eeglab-develop   # FACED 需要

# 2. 验环境
bash scripts/00_check_env.sh

# 3. TY 预处理（原始脑电 → 逐被试 pkl）
bash scripts/10_run_preprocessing.sh

# 4. TY 汇总 9 类
bash scripts/20_extract_9class.sh

# 5. TY 汇总 8 类自评（需问卷）
bash scripts/30_extract_8class.sh

# 6. FACED 预处理（EEGLAB .set → 拼接 → .mat）
bash scripts/40_run_faced.sh
```

## 与建模仓库的衔接

建模仓库的 `src/cfgs/data/*.yaml` 通过 `${oc.env:DAEST_PREP_ROOT}` 引用本仓库产出的 pkl / mat。
详见 [`docs/02_与建模仓库的衔接.md`](docs/02_与建模仓库的衔接.md)。

## 限制

见 [`docs/03_预处理限制.md`](docs/03_预处理限制.md)。
