import streamlit as st
import os
import json
import time
import requests
import base64
from datetime import datetime

# --- 基础配置 ---
st.set_page_config(page_title="Ulink IT Moments", page_icon="💻", layout="centered")

# Gemini API 配置
API_KEY = "" # 环境会自动注入
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={API_KEY}"

# 目录初始化
DATA_DIR = "data"
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
POSTS_FILE = os.path.join(DATA_DIR, "posts.json")

for d in [DATA_DIR, UPLOAD_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

if not os.path.exists(POSTS_FILE):
    with open(POSTS_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)

# --- 辅助函数 ---
def load_posts():
    try:
        with open(POSTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_posts(posts):
    with open(POSTS_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)

def call_gemini(prompt, system_instruction=""):
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": system_instruction}]} if system_instruction else None
    }
    try:
        response = requests.post(GEMINI_URL, json=payload, timeout=10)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return None
    return None

# --- UI 样式 ---
st.markdown("""
    <style>
    .main { background-color: #F8FAFC; }
    .stTextArea textarea { border-radius: 15px; border: 1px solid #E2E8F0; }
    .post-card {
        background: white;
        padding: 24px;
        border-radius: 24px;
        border: 1px solid #F1F5F9;
        margin-bottom: 24px;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05);
    }
    .author-name { font-weight: 900; font-size: 16px; color: #0F172A; }
    .post-time { font-size: 10px; color: #94A3B8; font-weight: 800; text-transform: uppercase; }
    .post-text { font-size: 15px; line-height: 1.6; color: #334155; margin: 16px 0; }
    .tag {
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
    .file-box {
        background: #F8FAFC;
        padding: 12px 16px;
        border-radius: 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-top: 8px;
        border: 1px solid transparent;
        transition: all 0.3s;
    }
    .file-box:hover { border-color: #DBEAFE; background: white; box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1); }
    .ai-summary {
        background: #0F172A;
        color: #DBEAFE;
        padding: 12px 16px;
        border-radius: 16px;
        font-size: 12px;
        font-weight: 700;
        margin-top: 12px;
        border-left: 4px solid #3B82F6;
    }
    </style>
""", unsafe_allow_html=True)

# --- 侧边栏 ---
with st.sidebar:
    st.markdown("### 🛡️ 身份验证")
    role = st.radio("当前角色", ["学生视角 (Student)", "教师管理 (Admin)"])
    is_admin = False
    if role == "教师管理 (Admin)":
        pwd = st.text_input("管理暗号", type="password")
        if pwd == "admin888":
            is_admin = True
            st.success("✨ 欢迎，IT 教师")
        elif pwd:
            st.error("🔑 暗号错误")
    
    st.divider()
    st.caption("Ulink ICT Repository v3.0\nPowered by Gemini AI")

# --- 主界面 ---
col_head1, col_head2 = st.columns([4, 1])
with col_head1:
    st.title("IT 资源朋友圈")
    st.markdown("<p style='color:#64748B; font-weight:bold; text-transform:uppercase; letter-spacing:0.2em; font-size:10px;'>Academic Resource Feed</p>", unsafe_allow_html=True)

# 搜索功能
search_q = st.text_input("🔍 搜索动态内容或文件名...", placeholder="输入关键词...")

# --- 教师发布区 ---
if is_admin:
    with st.expander("➕ 发布新资源动态", expanded=True):
        post_text = st.text_area("这一刻的想法...", placeholder="输入课堂要求、作业说明 (可不填)...", height=120)
        
        col_ai1, col_ai2 = st.columns(2)
        if col_ai1.button("✨ AI 润色文案"):
            if post_text:
                with st.spinner("AI 正在思考..."):
                    result = call_gemini(f"请润色这段 IT 课堂资源发布文案，使其专业且亲切：\n{post_text}", "你是一位资深信息技术老师。")
                    if result: st.session_state.post_text_buffer = result
            else:
                st.warning("请先输入文字")
        
        if 'post_text_buffer' in st.session_state:
            post_text = st.session_state.post_text_buffer
        
        tags_input = st.text_input("标签 (用空格分隔)", placeholder="如: Python 高一1班")
        uploaded_files = st.file_uploader("选取附件 (支持多选，无 1MB 限制)", accept_multiple_files=True)
        
        split_mode = False
        if uploaded_files and len(uploaded_files) > 1:
            split_mode = st.checkbox("一键分发（每个文件独立生成一条动态）")

        if st.button("🚀 立即发布", use_container_width=True):
            if not post_text and not uploaded_files:
                st.error("至少得写点什么或传个文件吧")
            else:
                with st.spinner("正在推送..."):
                    final_posts = load_posts()
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # 处理文件保存
                    saved_files = []
                    for f in uploaded_files:
                        f_path = os.path.join(UPLOAD_DIR, f.name)
                        with open(f_path, "wb") as fs:
                            fs.write(f.getbuffer())
                        saved_files.append({"name": f.name, "size": f"{f.size/1024:.1f} KB"})

                    if split_mode and len(saved_files) > 1:
                        for sf in saved_files:
                            final_posts.insert(0, {
                                "id": str(time.time()),
                                "text": post_text or "新资源发布",
                                "tags": tags_input.split() if tags_input else ["资源"],
                                "files": [sf],
                                "time": current_time,
                                "timestamp": time.time()
                            })
                    else:
                        final_posts.insert(0, {
                            "id": str(time.time()),
                            "text": post_text or "新资源发布",
                            "tags": tags_input.split() if tags_input else ["资源"],
                            "files": saved_files,
                            "time": current_time,
                            "timestamp": time.time()
                        })
                    
                    save_posts(final_posts)
                    st.session_state.pop('post_text_buffer', None)
                    st.success("发布成功！")
                    time.sleep(0.5)
                    st.rerun()

# --- 列表展示区 ---
posts = load_posts()
filtered_posts = [p for p in posts if search_q.lower() in p['text'].lower() or any(search_q.lower() in f['name'].lower() for f in p['files'])]

if not filtered_posts:
    st.info("暂无动态，请等待老师更新。")
else:
    for p in filtered_posts:
        with st.container():
            # 使用 HTML 渲染卡片
            st.markdown(f"""
                <div class="post-card">
                    <div style="display: flex; justify-content: space-between; align-items: start;">
                        <div style="display: flex; gap: 12px; align-items: center;">
                            <div style="width: 44px; height: 44px; background: #F1F5F9; border-radius: 12px; display: flex; align-items: center; justify-content: center; color: #94A3B8;">👤</div>
                            <div>
                                <div class="author-name">IT 教师</div>
                                <div class="post-time">{p['time']}</div>
                            </div>
                        </div>
                    </div>
                    <div class="post-text">{p['text']}</div>
                </div>
            """, unsafe_allow_html=True)
            
            # 文件下载区 (Streamlit 原生按钮)
            cols = st.columns([1, 4, 1])
            with cols[1]:
                for f in p['files']:
                    f_path = os.path.join(UPLOAD_DIR, f['name'])
                    if os.path.exists(f_path):
                        with open(f_path, "rb") as file_data:
                            st.download_button(
                                label=f"📥 下载: {f['name']} ({f['size']})",
                                data=file_data,
                                file_name=f['name'],
                                key=f"dl_{p['id']}_{f['name']}",
                                use_container_width=True
                            )
            
            # AI 摘要按钮
            if len(p['text']) > 30:
                if st.button(f"✨ AI 摘要", key=f"ai_{p['id']}"):
                    with st.spinner("AI 正在提炼..."):
                        summary = call_gemini(f"请简要总结这段话的重点：\n{p['text']}", "你是一个课程助教。")
                        if summary:
                            st.markdown(f'<div class="ai-summary">💡 AI 总结：{summary}</div>', unsafe_allow_html=True)
            
            # 标签展示
            st.markdown(" ".join([f'<span class="tag">#{t}</span>' for t in p.get('tags', [])]), unsafe_allow_html=True)

            # 管理员删除按钮
            if is_admin:
                if st.button(f"🗑️ 删除动态", key=f"del_{p['id']}"):
                    if st.checkbox(f"确认为 ID: {p['id']} 的动态执行粉碎操作？"):
                        new_posts = [x for x in posts if x['id'] != p['id']]
                        save_posts(new_posts)
                        # 注意：此处未删除实际物理文件以防误删，可根据需要增加 os.remove
                        st.success("已移除")
                        st.rerun()
            
            st.markdown("<div style='margin-bottom: 40px;'></div>", unsafe_allow_html=True)

st.markdown("---")
st.caption("© 2024 ULINK SENIOR HIGH · INFORMATION TECHNOLOGY")
