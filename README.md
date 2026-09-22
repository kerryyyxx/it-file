# 教师资料下发网页（Streamlit）
> 基于 Streamlit 实现的简易教学资料发布系统，教师上传文档发布动态，学生浏览、下载资料。
> ⚠️ Streamlit Cloud 免费容器会休眠，**本地磁盘上传的文件重启全部丢失**，本项目接入 Supabase 实现数据与文件持久化存储。

## ✨ 功能特性
- 🔐 教师管理入口：通过暗号进入发布模式
- 📎 支持上传 PDF / Word / PPT 等文档附件
- 📝 发布动态：填写内容、标签、上传资料
- 👨‍🎓 学生端：浏览全部动态、按标签筛选、下载资料
- 🔍 搜索：支持关键词搜索历史发布内容
- ☁️ 持久化存储：搭配 Supabase，应用休眠/重启数据不会丢失
- 📥 下载保留原始中文文件名

## 🛠️ 部署方式
### 方式1：Streamlit Cloud + Supabase（推荐，免费）
> Streamlit 负责网页界面；Supabase 负责永久保存帖子数据和上传文件。

#### 1. 准备 Supabase 后端
1. 前往 [supabase.com](https://supabase.com) 注册账号，**不需要绑定信用卡，使用免费套餐**
2. 新建项目：区域选择 `Southeast Asia (Singapore)`，设置数据库密码
3. 新建存储桶：左侧 `Storage` → `New bucket`，桶名称：`materials`，**勾选 Public bucket（公开桶）**
4. 打开 `SQL Editor` → `New query`，复制下面完整 SQL 执行
```sql
-- 创建帖子数据表
create table if not exists app_data (
  key text primary key,
  value text
);
insert into app_data (key, value) values ('posts', '[]')
on conflict (key) do nothing;

-- 开启行级安全，并允许应用读写帖子表
alter table app_data enable row level security;

drop policy if exists "app_data access" on app_data;
create policy "app_data access" on app_data
  for all using (true) with check (true);

-- Storage桶权限：允许匿名密钥读取、上传、删除文件
drop policy if exists "materials read" on storage.objects;
create policy "materials read" on storage.objects
  for select using (bucket_id = 'materials');

drop policy if exists "materials insert" on storage.objects;
create policy "materials insert" on storage.objects
  for insert with check (bucket_id = 'materials');

drop policy if exists "materials delete" on storage.objects;
create policy "materials delete" on storage.objects
  for delete using (bucket_id = 'materials');
```
5. 获取密钥：`Project Settings` → `API`
   - `Project URL`：项目地址
   - `Publishable key`（旧版叫 anon public key）：公开密钥
   - ❗ **不要使用 Secret keys / service_role 密钥**

#### 2. GitHub 仓库准备
仓库需要包含两个文件：
`app.py`：主程序代码
`requirements.txt`
```txt
streamlit
```

#### 3. Streamlit Cloud 关联部署
1. [share.streamlit.io](https://share.streamlit.io) 使用 GitHub 账号登录
2. 点击 `New app`，选择你的 GitHub 仓库、分支、主文件 `app.py`
3. 进入应用 `Settings` → `Secrets`，粘贴配置，替换为你自己的 Supabase 信息
```toml
SUPABASE_URL="[https://xxxx.supabase.co](https://xxxx.supabase.co)"
SUPABASE_KEY="sb_publishable_xxxx"
```
> ⚠️ SUPABASE_URL **末尾不要带斜杠 `/`**
4. 保存 Secrets，应用自动重启部署。

## 📦 Supabase 免费套餐说明
- 0元，无需信用卡；超额度不会自动扣费，只会限流
- 文件存储空间：1GB；数据库空间：500MB；每月下载流量：5GB
- 单文件最大限制：50MB，不适合上传大视频
- 项目连续一周无人访问会暂停，**数据不会删除，访问自动唤醒**

## 📖 使用说明
1. 打开网页，输入**管理暗号**进入教师发布模式（代码内可修改暗号）
2. 填写动态内容、标签，选择本地文件上传，点击发布
3. 学生无需登录，直接浏览全部动态，点击下载获取资料
4. 教师可以删除已发布动态，云端文件同步删除

## ⚠️ 重要注意事项
1. **不配置 Supabase 时会回退本地临时模式**：上传文件仅存在容器内存，应用休眠重启全部清空，仅用于测试。
2. 旧版本本地模式下已经发布的内容**无法自动迁移到 Supabase**，需要重新发布。
3. Supabase 存储桶内部保存随机英文文件名，页面与下载会还原原始中文文件名。
4. 不要将 Supabase 密钥硬编码写在代码中，必须放在 Streamlit Secrets。

## 📂 项目结构
```
.
├── app.py             # streamlit主应用
└── requirements.txt   # 依赖声明
```

## 🐛 常见问题排查
1. `PGRST125 Invalid path specified in request URL`
> SUPABASE_URL 末尾多斜杠或者粘贴多余字符，删除尾部 `/`。

2. `400 InvalidKey`
> 老版本代码中文文件名报错，使用本仓库最新 app.py，内部自动转换随机文件名。

3. 文件上传报错 permission denied
> 检查 SQL 是否完整运行；桶名字严格为 `materials`；桶设置为 Public bucket。

4. 侧边栏显示「本地临时」而不是「Supabase云端」
> Secrets 没有配置成功，检查 `SUPABASE_URL` 和 `SUPABASE_KEY` 是否复制正确。

## 📜 License
MIT License，仅供教学学习使用。

---

你可以直接复制全部内容，在GitHub仓库点 `Add file → Create new file`，文件名写 `README.md`，粘贴全部文本，提交即可。
如果你需要，我可以帮你再精简一版（简短版README）。
