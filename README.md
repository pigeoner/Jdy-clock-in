## 简道云自动打卡脚本（自用）

> 2023.1.9 更新：由于2022.12.6之后不再需要简道云打卡，且本仓库代码长期未更新早已过时，故不再维护

#### 1. 使用

- 学生版用户根据提示配置 `settings.yaml`，教师版不需要配置
- 学生版用户终端运行 `python jdy_student.py`，教师版用户终端运行 `python jdy_teacher.py`
- 首次运行需要通过企业微信扫码获取 `cookie` ，并自动生成完整的配置文件（学生版配置文件为 `settings.yaml` ，教师版配置文件为 `config.json`），之后不需要重复扫码

#### 2. 注意事项
- `cookie` 似乎不会过期，但 `X-CSRF-Token` 的值会过期
- (学生版）如果打卡失败，可以尝试重新配置 `settings.yaml`：删除现有的 `settings.yaml`，将 `settings_default.yaml` 在同路径下复制一份并重命名为 `settings.yaml`
- 在提交的时候，缺少了一项请求载荷数据 `data-op-id` ，尚不清楚是否会造成影响。
- **因为还可能存在一些未知的bug，所以慎用！**
