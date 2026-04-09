import streamlit as st
import os
import json
import time
from datetime import datetime

# --- 1. 基础配置 ---
st.set_page_config(page_title="Ulink IT Feed", page_icon="💻", layout="centered")

# 数据存储路径
DATA_DIR = "data"
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
DB_FILE = os.path.join(DATA_DIR, "database.json")

# 初始化文件夹和数据库
for d in [DATA_DIR, UPLOAD_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)

# --- 2. 数据处理函数 ---
def load_data():
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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
    is_admin = (pwd == "admin888")
    
    if is_admin:
        st.success("✨ 教师模式已激活")
    else:
        st.info("学生浏览模式")
    
    st.divider()
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
                saved_files_meta = []
                for f in new_files:
                    f_path = os.path.join(UPLOAD_DIR, f.name)
                    with open(f_path, "wb") as fs:
                        fs.write(f.getbuffer())
                    saved_files_meta.append({
                        "name": f.name,
                        "size": f"{f.size / (1024*1024):.2f} MB"
                    })
                
                new_post = {
                    "id": str(time.time()),
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
tag_cols = st.columns(len(sorted_tags) if len(sorted_tags) > 0 else 1)
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
                        f_path = os.path.join(UPLOAD_DIR, f["name"])
                        if os.path.exists(f_path):
                            with open(f_path, "rb") as file_data:
                                st.download_button(
                                    label=f"📥 下载: {f['name']} ({f['size']})",
                                    data=file_data,
                                    file_name=f['name'],
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
                        # 物理删除文件
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
