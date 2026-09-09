# 原始数据来源

不在本仓库，需从以下位置获取：

| 数据 | 路径 | 大小 |
|---|---|---|
| TY 原始脑电 .bdf | `${DAEST_DATA_ROOT}/data-tongyong/原始数据/脑电近红外/标准脑电/` | 46 GB |
| TY 问卷 CSV | `${DAEST_DATA_ROOT}/data-tongyong/原始数据/问卷/`（涉及被试信息，不随仓库分发；本仓库仅收录 3 名被试样例与列定义，见 `data/README.md`） | 3.7 MB |
| FACED 原始 .bdf | `${DAEST_DATA_ROOT}/data-faced/Data/subXXX/{data.bdf, evt.bdf}` | ~40 GB |
| FACED 被试清单 | `${DAEST_DATA_ROOT}/data-faced/一些背景/Recording_info.csv` | — |
| FACED 播放顺序 | `${DAEST_DATA_ROOT}/data-faced/Data/subXXX/After_remarks.mat` | — |

## TY 原始脑电格式

- 每个被试一个目录，内含 `data*.bdf` + `evt*.bdf` 或 `data_raw.fif`
- 第一批（001–047）：μV 单位
- 第二批（048+）：V 单位
- 观影任务：触发码标记视频开始
- 讲述任务：触发码 22 标记视频开始

## FACED 原始数据格式

- 每被试一个目录 `Data/subXXX/`，内含 `data.bdf` + `evt.bdf` + `After_remarks.mat`
- 触发码：`event_id=102` 切分 30 s 片段；视频触发码为 `1..28`
- 播放顺序从 `After_remarks.mat` 的 `vid` 字段读取，在 `data_concat` 中完成重排拼接
- **预处理为纯 Python/MNE，不需要 MATLAB 或 EEGLAB**
  （`legacy/` 下基于 `.set` 的 EEGLAB 旁支未用于任何已发表结果，见 `docs/04_版本溯源.md`）

## 问卷 CSV 结构

每个被试一个子目录（如 `001/`），内含：

| 文件 | 内容 |
|---|---|
| `exp0_*_rating.csv` | 观影任务：8 维情绪评分 + 播放顺序 |
| `exp1_*_rating.csv` | 讲述任务：8 维情绪评分 + 播放顺序 |

## 授权

原始脑电数据涉及人类被试，需遵循伦理审查协议，不公开分发。
