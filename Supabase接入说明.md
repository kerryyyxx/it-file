# Supabase 接入说明（让数据永久保留）

改造目标：**文件存 Supabase Storage（公开桶），帖子数据存 Supabase 数据库（app\_data 表）**。

Streamlit 应用只负责界面，睡眠 / 重启都不会再丢数据。

总耗时约 15 分钟，全程免费（免费版含 1GB 存储，教学资料足够）。



***

## 第一步：注册 Supabase 并创建项目（5 分钟）



1. 打开 [https://supabase.com](https://supabase.com) → Sign Up 注册（可用 GitHub 账号）。

2. 登录后点 **New project**：

* Name：随意，如 `ulink-materials`

* Database Password：记下来（以后基本用不到）

* Region：选 **Southeast Asia (Singapore)**（离国内近、速度快）

1. 等待 1–2 分钟创建完成。

## 第二步：创建公开存储桶（2 分钟）



1. 左侧菜单 **Storage** → **New bucket**：

* Name：填 `materials`（必须和 app.py 里的 `BUCKET = "materials"` 一致）

* **Public bucket：打开**

1. 创建后点击该桶 → **Settings**，确认 Public 已开启（这样学生不需要登录也能直接下载）。

## 第三步：运行完整 SQL（2 分钟）



1. 左侧菜单 **SQL Editor** → New query。

2. 粘贴**下面这一整段** SQL 并点 **Run**：



```
\-- 1) 帖子数据表

create table if not exists app\_data (

&#x20; key text primary key,

&#x20; value text

);

insert into app\_data (key, value) values ('posts', '\[]')

on conflict (key) do nothing;

\-- 2) 开启行级安全，并允许应用（anon 密钥）读写帖子表

alter table app\_data enable row level security;

drop policy if exists "app\_data access" on app\_data;

create policy "app\_data access" on app\_data

&#x20; for all using (true) with check (true);

\-- 3) 允许应用通过 anon 密钥向 materials 桶上传 / 下载 / 删除文件

drop policy if exists "materials read" on storage.objects;

create policy "materials read" on storage.objects

&#x20; for select using (bucket\_id = 'materials');

drop policy if exists "materials insert" on storage.objects;

create policy "materials insert" on storage.objects

&#x20; for insert with check (bucket\_id = 'materials');

drop policy if exists "materials delete" on storage.objects;

create policy "materials delete" on storage.objects

&#x20; for delete using (bucket\_id = 'materials');
```

> **弹窗说明**
>
> ：运行时如果弹出 "Potential issue detected"（提示表没有启用 Row Level Security），点 
>
> **Run and enable RLS**
>
>  即可，脚本本身已包含全部所需权限。这段 SQL 可重复执行，跑错或漏了重跑一次不会出问题。

## 第四步：复制项目密钥（1 分钟）



1. 左侧菜单 **Project Settings** → **API**。

2. 复制两个值：

* **Project URL**：形如 `https://xxxx.supabase.co`

* **Publishable key**：新版界面叫 Publishable key（`sb_publishable_...` 开头）；旧版界面叫 anon public key（`eyJhbGciOi...` 开头），两者是同一个东西、作用相同。

* ⚠️ 页面上的 **Secret keys**（`sb_secret_...`，对应旧版 service_role）是超级权限密钥，**绝对不要复制进应用**。

## 第五步：把密钥填进应用（2 分钟）

### 部署在 Streamlit Cloud（正式使用）



1. 在 [https://share.streamlit.io](https://share.streamlit.io) 打开你的应用 → **Settings** → **Secrets**。

2. 粘贴（把值替换成你自己的）：



```
SUPABASE\_URL="https://xxxx.supabase.co"

SUPABASE\_KEY="eyJhbGciOi..."
```



1. 保存后点 **Rerun** 重启应用。侧边栏会显示「存储：Supabase 云端（持久）」。

2. 新版代码已改用标准 HTTP 直连 Supabase 接口，`requirements.txt` 保持原样即可（如之前加过 `supabase` 也可以删掉）。

### 本地调试



1. 在项目根目录创建 `.streamlit/secrets.toml`：



```
SUPABASE\_URL="https://xxxx.supabase.co"

SUPABASE\_KEY="eyJhbGciOi..."
```



1. 安装依赖：`pip install streamlit`（新版代码不再需要 supabase 库）

2. 运行：`streamlit run app.py`

> 管理暗号可写进 Secrets：
>
> `ADMIN_PWD="你的新暗号"`
>
> （不写则仍用原来的 
>
> `admin888`
>
> ）。

## 验证是否成功



1. 用管理暗号进入教师模式，发布一条带文件的动态 → 显示「✅ 动态已分发至全班」。

2. 打开 Supabase → **Storage** → `materials` 桶，能看到刚上传的文件。

3. 打开 Supabase → **Table Editor** → `app_data`，能看到 posts 数据。

4. 把 Streamlit 应用重启（甚至第二天再打开），资料依然在。

## 常见问题



| 问题          | 处理                                                             |
| ----------- | -------------------------------------------------------------- |
| 侧边栏显示「本地临时」 | Secrets 没生效：检查 `SUPABASE_URL` / `SUPABASE_KEY` 是否填对，保存后要 Rerun |
| 上传报错        | 确认桶名是 `materials`、且已开启 Public；再把第三步的完整 SQL 重跑一遍（含桶权限）          |
| 上传报错 'dict' object has no attribute 'text' | supabase 库的版本兼容问题；新版代码已改为直连 REST 接口，重新上传最新版 app.py 即可 |
| 上传报错 PGRST125 / Invalid path | Secrets 里 `SUPABASE_URL` 填错：结尾多了 `/` 或 .supabase.co 后面有多余内容。新版代码已自动纠错；也可直接去 Secrets 把 URL 改成形如 `https://xxxx.supabase.co`（结尾无斜杠） |
| 上传报错 InvalidKey（中文文件名） | Supabase 对象名只允许 ASCII 字符（AWS 命名规范）。新版代码已自动把云端文件名改为随机 ASCII 名，界面和下载仍显示原始中文名，重新上传最新版 app.py 即可 |
| 学生下载按钮转圈    | 多为大文件首次拉取，稍等即可；失败会自动变成「打开」链接按钮                                 |
| 旧数据（改造前发的）  | 无法自动迁移，需要在新模式下重新发布；之后的资料都永久保留                                  |
| 超过免费额度      | 免费版 1GB 存储 + 5GB 流量，教学资料基本用不完；不够可在 Supabase 升级                 |