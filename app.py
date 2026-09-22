import streamlit as st
import os
import json
import time
import urllib.request
from datetime import datetime

# --- 1. 基础配置 ---
st.set_page_config(page_title="Ulink IT Feed", page_icon="💻", layout="centered")


# ========== Supabase 持久化配置（核心改造）==========
# 读取 Streamlit Secrets：
#   Streamlit Cloud 部署后：Settings → Secrets 里添加
#     SUPABASE_URL="https://xxxx.supabase.co"
#     SUPABASE_KEY="sb_publishable_..."   （新版界面叫 Publishable key；旧版叫 anon public key，两者等价）
#     ADMIN_PWD="你的管理暗号"   （可选，不填则默认 admin888）
#   本地运行：在项目根目录建 .streamlit/secrets.toml，内容同上
#   注意：Secret keys（sb_secret_...，旧版 service_role）是超级权限密钥，绝不能放进应用

def _get_secret(name, default=""):
    """兼容各种 Streamlit 版本的安全读取 Secrets 方式"""
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


SUPABASE_URL = _get_secret("SUPABASE_URL").strip()
SUPABASE_KEY = _get_secret("SUPABASE_KEY").strip()
ADMIN_PWD = _get_secret("ADMIN_PWD", "admin888")
BUCKET = "materials"        # 公开桶名（在 Supabase Storage 里创建，需开启 Public）
DATA_KEY = "posts"          # app_data 表里保存帖子数据的行 key

# 本地目录仅作为“未配置 Supabase 时的兜底”，配置后不再依赖它
DATA_DIR = "data"
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
DB_FILE = os.path.join(DATA_DIR, "database.json")
for d in [DATA_DIR, UPLOAD_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

# 初始化 Supabase 客户端（未配置密钥时自动退回本地临时模式）
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY)
_sb = None
if USE_SUPABASE:
    try:
        from supabase import create_client
        _sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        _sb = None
        USE_SUPABASE = False
        st.warning(f"⚠️ Supabase 客户端初始化失败，已退回本地临时模式：{e}")

if not USE_SUPABASE:
    st.info("ℹ️ 尚未配置 Supabase（Secrets 缺少 SUPABASE_URL / SUPABASE_KEY），当前为本地临时模式，数据会在应用重启后丢失。详见《Supabase接入说明》。")


# --- 2. 数据处理函数（优先 Supabase，失败时退回本地） ---
def public_url(path):
    """根据存储路径生成 Supabase 公开下载地址"""
    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{path}"


def load_data():
    if USE_SUPABASE:
        try:
            res = _sb.table("app_data").select("value").eq("key", DATA_KEY).limit(1).execute()
            if res.data:
                return json.loads(res.data[0]["value"])
            return []
        except Exception:
            pass  # 读取失败时退回本地，避免页面崩溃
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_data(data):
    if USE_SUPABASE:
        try:
            _sb.table("app_data").upsert(
                {"key": DATA_KEY, "value": json.dumps(data, ensure_ascii=False)}
            ).execute()
            return
        except Exception as e:
            st.error(f"保存到 Supabase 失败：{e}，已退回本地临时保存")
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def upload_file(post_id, f):
    """把上传文件写入持久化存储，返回文件元信息；失败返回 None"""
    if USE_SUPABASE:
        try:
            f_path = f"uploads/{post_id}/{f.name}"   # 按动态 id 分组，避免同名覆盖
            _sb.storage.from_(BUCKET).upload(
                f_path,
                f.getvalue(),
                {"content-type": f.type or "application/octet-stream"},
            )
            return {
                "name": f.name,
                "size": f"{f.size / (1024 * 1024):.2f} MB",
                "url": public_url(f_path),
                "path": f_path,
            }
        except Exception as e:
            st.error(f"文件 {f.name} 上传到 Supabase 失败：{e}")
            return None
    else:
        # 本地临时模式（保持原有行为）
        f_path = os.path.join(UPLOAD_DIR, f.name)
        with open(f_path, "wb") as fs:
            fs.write(f.getbuffer())
        return {"name": f.name, "size": f"{f.size / (1024 * 1024):.2f} MB"}


@st.cache_data(ttl=600, show_spinner=False)
def _fetch_file(url):
    """从公开 URL 拉取文件内容供下载按钮使用（带缓存，避免每次刷新都下载）"""
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return resp.read()
    except Exception:
        return None


# --- 3. 注入 CSS 样式 (完全还原演示版视觉) ---
st.markdown("""
    <style>
    .main { background-color: #F8FAFC; }
    /* 朋友圈卡片样式 */
    .moment-card {
        background: white;
        padding: 24px;
        border-radius: 24px;
        border: 1px solid #F1F5F9;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05);
    }
    .author-info { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
    .avatar { width: 44px; height: 44px; background: #3B82F6; border-radius: 12px; display: flex; align-items: center; justify-content: center; color: white; font-weight: 900; }
    .author-name { font-weight: 900; font-size: 15px; color: #1E293B; line-height: 1; }
    .post-time { font-size: 10px; color: #94A3B8; font-weight: bold; text-transform: uppercase; margin-top: 4px; }
    .post-text { font-size: 16px; line-height: 1.8; color: #334155; margin: 16px 0; white-space: pre-wrap; }
    /* 标签样式 */
    .tag-item {
        display: inline-block;
        background: #EFF6FF;
        color: #2563EB;
        font-size: 10px;
        font-weight: 900;
        padding: 4px 12px;
        border-radius: 8px;
        margin-right: 8px;
        text-transform: uppercase;
    }
    /* 隐藏 Streamlit 默认的一些元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 4. 侧边栏：管理权限 ---
with st.sidebar:
    st.markdown("### 🛡️ 身份验证")
    pwd = st.text_input("管理暗号", type="password")
    is_admin = (pwd == ADMIN_PWD)

    if is_admin:
        st.success("✨ 教师模式已激活")
    else:
        st.info("学生浏览模式")

    st.divider()
    st.caption("存储：" + ("Supabase 云端（持久）" if USE_SUPABASE else "本地临时（重启会丢）"))
    st.caption("ULINK ICT REPOSITORY v3.0")

# --- 5. 主界面头部 ---
st.title("Ulink IT 资源站")
st.markdown("<p style='color:#3B82F6; font-weight:900; letter-spacing:0.3em; font-size:11px; margin-top:-15px; text-transform:uppercase;'>Academic Moments Feed</p>", unsafe_allow_html=True)

# --- 6. 教师发布区 ---
if is_admin:
    with st.expander("📤 发布新教学动态", expanded=False):
        new_text = st.text_area("文案内容 (选填)", placeholder="输入对文件的说明，如作业要求...")
        new_tags = st.text_input("标签 (空格分隔)", placeholder="如: Python 实验")
        # Streamlit 自带的文件上传列表就很清晰
        new_files = st.file_uploader("选取资源文件", accept_multiple_files=True)

        if st.button("立即分发资源", use_container_width=True):
            if not new_text and not new_files:
                st.warning("内容不能为空")
            else:
                posts = load_data()
                new_id = str(time.time())
                saved_files_meta = []
                for f in new_files:
                    meta = upload_file(new_id, f)
                    if meta:
                        saved_files_meta.append(meta)

                new_post = {
                    "id": new_id,
                    "text": new_text or "新资源发布",
                    "tags": new_tags.split() if new_tags else ["资源"],
                    "files": saved_files_meta,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                posts.insert(0, new_post)
                save_data(posts)
                st.toast("✅ 动态已分发至全班")
                time.sleep(1)
                st.rerun()

# --- 7. 搜索与标签筛选区 ---
posts = load_data()

# 自动汇总所有标签
all_tags = set(["全部"])
for p in posts:
    for t in p.get("tags", []):
        all_tags.add(t)
sorted_tags = sorted(list(all_tags))

st.write("") # 间距
search_q = st.text_input("🔍 搜索关键词或文件名...", placeholder="输入搜索内容...")

# 标签过滤按钮行
selected_tag = st.session_state.get("selected_tag", "全部")

# 使用按钮组模拟标签栏
cols = st.columns(len(sorted_tags))
for i, tag in enumerate(sorted_tags):
    if cols[i].button(tag, key=f"tag_btn_{tag}", use_container_width=True,
                      type="primary" if selected_tag == tag else "secondary"):
        st.session_state.selected_tag = tag
        st.rerun()

# --- 8. 列表渲染逻辑 ---
current_tag = st.session_state.get("selected_tag", "全部")

# 综合过滤
filtered_posts = [
    p for p in posts
    if (search_q.lower() in p["text"].lower() or any(search_q.lower() in f["name"].lower() for f in p["files"]))
    and (current_tag == "全部" or current_tag in p.get("tags", []))
]

st.divider()

if not filtered_posts:
    st.markdown("<center style='opacity:0.3; padding:50px;'>没有找到匹配的资源</center>", unsafe_allow_html=True)
else:
    for p in filtered_posts:
        # 卡片容器
        with st.container():
            st.markdown(f"""
                <div class="moment-card">
                    <div class="author-info">
                        <div class="avatar">IT</div>
                        <div>
                            <div class="author-name">IT 教师</div>
                            <div class="post-time">{p['time']}</div>
                        </div>
                    </div>
                    <div class="post-text">{p['text']}</div>
                </div>
            """, unsafe_allow_html=True)

            # 下载按钮区域
            if p["files"]:
                dl_cols = st.columns([1, 6, 1])
                with dl_cols[1]:
                    for f in p["files"]:
                        if f.get("url"):
                            # Supabase 持久化模式：从公开 URL 下载
                            data_bytes = _fetch_file(f["url"])
                            if data_bytes is not None:
                                st.download_button(
                                    label=f"📥 下载: {f['name']} ({f['size']})",
                                    data=data_bytes,
                                    file_name=f["name"],
                                    key=f"dl_{p['id']}_{f['name']}",
                                    use_container_width=True
                                )
                            else:
                                st.link_button(
                                    label=f"🌐 打开: {f['name']} ({f['size']})",
                                    url=f["url"],
                                    key=f"dl_{p['id']}_{f['name']}",
                                    use_container_width=True
                                )
                        else:
                            # 兼容历史数据：从本地文件下载
                            f_path = os.path.join(UPLOAD_DIR, f["name"])
                            if os.path.exists(f_path):
                                with open(f_path, "rb") as file_data:
                                    st.download_button(
                                        label=f"📥 下载: {f['name']} ({f['size']})",
                                        data=file_data,
                                        file_name=f["name"],
                                        key=f"dl_{p['id']}_{f['name']}",
                                        use_container_width=True
                                    )

            # 标签展示
            tags_html = "".join([f'<span class="tag-item">#{t}</span>' for t in p.get("tags", [])])
            st.markdown(f"<div>{tags_html}</div>", unsafe_allow_html=True)

            # 管理功能：删除
            if is_admin:
                col_btn1, col_btn2 = st.columns([7, 1])
                with col_btn2:
                    # 使用 streamlit 的二次确认按钮逻辑
                    if st.button("🗑️", key=f"del_{p['id']}", help="永久粉碎此动态"):
                        if USE_SUPABASE:
                            # 删除 Supabase 里的文件（含历史兼容：无 path 的旧数据跳过）
                            paths = [f["path"] for f in p["files"] if f.get("path")]
                            if paths:
                                try:
                                    _sb.storage.from_(BUCKET).remove(paths)
                                except Exception as e:
                                    st.warning(f"删除云端文件失败：{e}")
                            _fetch_file.clear()
                        else:
                            # 本地临时模式：物理删除文件
                            for f in p["files"]:
                                f_p = os.path.join(UPLOAD_DIR, f["name"])
                                if os.path.exists(f_p):
                                    os.remove(f_p)
                        # 更新数据库
                        new_all_posts = [x for x in posts if x["id"] != p["id"]]
                        save_data(new_all_posts)
                        st.toast("已物理删除资源")
                        time.sleep(1)
                        st.rerun()

            st.write("") # 底部留白

st.markdown("<br><br><p style='text-align:center; color:#CBD5E1; font-size:10px; font-weight:bold;'>© 2024 ULINK ICT DEPT · ALL RIGHTS RESERVED</p>", unsafe_allow_html=True)
