import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import json
import sys
import os

# 現在のディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager
from openai_integration import OpenAIIntegration

# ページ設定
st.set_page_config(
    page_title="ショート動画台本自動生成ツール",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# データベースとOpenAI統合の初期化
@st.cache_resource
def init_services():
    db = DatabaseManager()
    openai_service = OpenAIIntegration()
    return db, openai_service

db, openai_service = init_services()

# 新規追加：入力フォームクリア機能
def clear_form_inputs():
    """入力フォームをクリアする関数"""
    # セッションステートから入力値を削除
    keys_to_clear = []
    for key in st.session_state.keys():
        if key.startswith('input_') or key.startswith('form_'):
            keys_to_clear.append(key)
    
    for key in keys_to_clear:
        del st.session_state[key]

# サイドバーナビゲーション
st.sidebar.title("🎬 ショート動画台本ツール")
st.sidebar.markdown("---")

# 商材カテゴリー選択（全ページ共通）
categories = db.get_product_categories()
category_options = [""] + [f"{cat[0]}: {cat[1]}" for cat in categories]
selected_category = st.sidebar.selectbox("📂 商材カテゴリー", category_options)

if selected_category:
    category_id = int(selected_category.split(":")[0])
    category_name = selected_category.split(":")[1].strip()
else:
    category_id = None
    category_name = None

# ナビゲーション（競合分析を削除）
page = st.sidebar.selectbox(
    "ページ選択",
    ["🏠 ホーム", "✨ 台本生成", "📚 台本ライブラリ", "📊 成果管理", "📈 レポート", "⚙️ 設定"]
)

st.sidebar.markdown("---")
st.sidebar.info("💡 使用方法：まず商材カテゴリーを選択してから各機能をご利用ください")

# メインコンテンツ
if page == "🏠 ホーム":
    st.title("🎬 ショート動画台本自動生成ツール")
    st.markdown("---")
    
    # 概要説明
    st.markdown("""
    ## 🎯 ツールの特徴
    
    このツールは、**強化学習**を活用した次世代の広告台本自動生成システムです。
    
    ### 📊 主な機能
    
    1. **📚 効果的台本の蓄積**
       - 過去に効果の良かった台本を登録・管理
       - 商材カテゴリー別に分類
       
    2. **✨ AI台本自動生成**
       - 蓄積されたデータから最適な台本を自動生成
       - 複数パターンの同時生成
       
    3. **📊 配信結果の学習**
       - CTR、CPC、mCVR、mCPA、CVR、CPAの結果を入力
       - 消化金額による重み付け学習
       
    4. **🚀 継続的な精度向上**
       - 配信結果から自動学習
       - 商材・プラットフォーム別の最適化
       
    5. **🚫 NGワード管理**
       - 商材別レギュレーション対応
       - 自動除外機能
    """)
    
    # 統計情報
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        effective_count = len(db.get_effective_scripts())
        st.metric("効果的台本数", f"{effective_count}件")
    
    with col2:
        category_count = len(db.get_product_categories())
        st.metric("商材カテゴリー", f"{category_count}件")
    
    with col3:
        # 生成された台本数
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM generated_scripts")
        generated_count = cursor.fetchone()[0]
        conn.close()
        st.metric("生成済み台本", f"{generated_count}件")
    
    with col4:
        # 配信結果数
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM campaign_results")
        result_count = cursor.fetchone()[0]
        conn.close()
        st.metric("配信結果", f"{result_count}件")
    
    # 学習統計情報
    st.markdown("---")
    st.subheader("🤖 AI学習状況")
    
    if category_id:
        # 選択されたカテゴリーの学習統計
        stats = db.get_learning_statistics(category_id)
        if stats:
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**学習パターン統計**")
                for pattern_type, count, avg_score in stats:
                    st.metric(f"{pattern_type}", f"{count}件", f"平均スコア: {avg_score:.2f}")
            
            with col2:
                # 最も効果的なパターン
                patterns = db.get_learning_patterns(category_id, min_effectiveness=0.5)
                if patterns:
                    st.write("**効果的な学習パターン**")
                    for pattern_type, content, score, frequency in patterns[:5]:
                        st.write(f"- {pattern_type}: {content} (スコア: {score:.2f})")
        else:
            st.info("まだ学習データがありません。配信結果を入力して学習を開始してください。")
    else:
        st.info("商材カテゴリーを選択すると、学習状況を確認できます。")
    
    st.markdown("---")
    st.info("💡 まずは「⚙️ 設定」から商材カテゴリーを登録し、「📚 台本ライブラリ」で効果的な台本を蓄積してから台本生成をお試しください！")

elif page == "✨ 台本生成":
    st.title("✨ AI台本自動生成")
    st.markdown("---")
    
    if not category_id:
        st.warning("⚠️ 商材カテゴリーを選択してください")
        st.stop()
    
    # NGワード警告表示
    ng_words = db.get_ng_words(category_id)
    if ng_words:
        st.info(f"🚫 このカテゴリーには {len(ng_words)} 個のNGワードが設定されています。台本生成時に自動的に除外されます。")
    
    # セッションステートの初期化
    if 'generated_scripts' not in st.session_state:
        st.session_state.generated_scripts = []
    if 'saved_scripts' not in st.session_state:
        st.session_state.saved_scripts = set()
    
    # 台本生成フォーム（トーン選択を削除）
    with st.form("script_generation_form"):
        st.subheader(f"📂 {category_name} の台本生成")
        
        col1, col2 = st.columns(2)
        
        with col1:
            target_audience = st.text_input("🎯 ターゲット層", placeholder="例：20-30代女性")
            platform = st.selectbox("📱 プラットフォーム", ["TikTok", "Instagram Reels", "YouTube Shorts", "Meta"])
            script_length = st.selectbox("⏱️ 台本の長さ", ["15秒", "30秒", "60秒"])
        
        with col2:
            generation_count = st.slider("🔢 生成数", 1, 5, 3)
            use_effective_scripts = st.checkbox("📚 効果的台本を参考にする", value=True)
            
            # 学習データの活用状況を表示
            patterns = db.get_learning_patterns(category_id, platform)
            if patterns:
                st.info(f"🤖 {len(patterns)}個の学習パターンを活用")
            else:
                st.info("🤖 基本設定で生成（学習データなし）")
        
        generate_button = st.form_submit_button("🚀 台本生成", use_container_width=True)
    
    if generate_button:
        # 効果的台本を取得
        effective_scripts = []
        if use_effective_scripts:
            effective_scripts = db.get_effective_scripts(category_id, platform)
        
        # 台本生成
        with st.spinner("🤖 AIが台本を生成中..."):
            try:
                scripts = []
                for i in range(generation_count):
                    script_data = openai_service.generate_script(
                        category=category_name,
                        target_audience=target_audience,
                        platform=platform,
                        script_length=script_length,
                        reference_scripts=effective_scripts,
                        category_id=category_id
                    )
                    scripts.append(script_data)
                
                # 生成された台本をセッションステートに保存
                st.session_state.generated_scripts = scripts
                st.session_state.saved_scripts = set()  # 保存状態をリセット
                
                st.success(f"✅ {generation_count}件の台本を生成しました！")
                
                # NGワード検出の通知
                if ng_words:
                    st.info("🚫 NGワードチェックが適用されました。規制対象の単語は自動的に除外されています。")
                
            except Exception as e:
                st.error(f"❌ 台本生成中にエラーが発生しました: {str(e)}")
    
    # 生成された台本を表示（セッションステートから）
    if st.session_state.generated_scripts:
        st.markdown("---")
        st.subheader("📝 生成された台本")
        
        for i, script in enumerate(st.session_state.generated_scripts, 1):
            with st.expander(f"📝 生成台本 {i}: {script.get('title', 'タイトル未設定')}"):
                st.markdown(f"**🎣 フック:**\n{script.get('hook', '')}")
                st.markdown(f"**💬 メインコンテンツ:**\n{script.get('main_content', '')}")
                st.markdown(f"**📢 CTA:**\n{script.get('call_to_action', '')}")
                
                # 保存状態の確認
                if i in st.session_state.saved_scripts:
                    st.success(f"✅ 台本{i}は既に保存済みです")
                else:
                    # 台本保存ボタン
                    if st.button(f"💾 台本{i}を保存", key=f"save_{i}"):
                        try:
                            conn = db.get_connection()
                            cursor = conn.cursor()
                            cursor.execute('''
                                INSERT INTO generated_scripts 
                                (category_id, title, hook, main_content, call_to_action, script_content, platform, generation_source)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (category_id, script.get('title', ''), script.get('hook', ''), 
                                  script.get('main_content', ''), script.get('call_to_action', ''),
                                  script.get('script_content', ''), platform, '統合AI生成'))
                            conn.commit()
                            conn.close()
                            
                            # 保存状態を更新
                            st.session_state.saved_scripts.add(i)
                            st.success(f"✅ 台本{i}を保存しました！")
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ 保存中にエラーが発生しました: {str(e)}")

elif page == "📚 台本ライブラリ":
    st.title("📚 台本ライブラリ")
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["📝 効果的台本", "🤖 生成済み台本"])
    
    with tab1:
        st.subheader("📝 効果的台本管理")
        
        # 効果的台本の追加
        with st.expander("➕ 新しい効果的台本を追加"):
            if not category_id:
                st.warning("⚠️ 商材カテゴリーを選択してください")
            else:
                with st.form("add_effective_script"):
                    title = st.text_input("📋 台本タイトル", placeholder="例：夏のダイエット商品訴求", key="form_effective_title")
                    platform = st.selectbox("📱 プラットフォーム", ["TikTok", "Instagram Reels", "YouTube Shorts", "Meta"], key="form_effective_platform")
                    hook = st.text_area("🎣 フック", placeholder="視聴者の注意を引く冒頭部分", key="form_effective_hook")
                    main_content = st.text_area("💬 メインコンテンツ", placeholder="商品の特徴や効果を説明", key="form_effective_main")
                    cta = st.text_area("📢 CTA", placeholder="行動を促す部分", key="form_effective_cta")
                    reason = st.text_area("✨ 効果的な理由", placeholder="なぜこの台本が効果的だったか", key="form_effective_reason")
                    
                    if st.form_submit_button("💾 効果的台本を追加"):
                        try:
                            script_id = db.add_effective_script(category_id, title, hook, main_content, cta, platform, reason)
                            st.success(f"✅ 効果的台本を追加しました！（ID: {script_id}）")
                            
                            # 新規追加：入力フォームをクリア
                            clear_form_inputs()
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ エラーが発生しました: {str(e)}")
        
        # 効果的台本の一覧
        st.subheader("📋 効果的台本一覧")
        
        try:
            effective_scripts = db.get_effective_scripts(category_id)
            if effective_scripts:
                for script in effective_scripts:
                    # データ構造を安全に取得
                    script_id = script[0] if len(script) > 0 else "不明"
                    script_title = script[2] if len(script) > 2 else "タイトル不明"
                    script_hook = script[3] if len(script) > 3 else ""
                    script_main = script[4] if len(script) > 4 else ""
                    script_cta = script[5] if len(script) > 5 else ""
                    script_platform = script[7] if len(script) > 7 else "プラットフォーム不明"
                    script_reason = script[8] if len(script) > 8 else ""
                    script_created = script[9] if len(script) > 9 else "作成日不明"
                    script_category = script[15] if len(script) > 15 else "カテゴリー不明"
                    
                    with st.expander(f"📝 {script_title} ({script_platform} - {script_category})"):
                        if script_hook:
                            st.markdown(f"**🎣 フック:**\n{script_hook}")
                        if script_main:
                            st.markdown(f"**💬 メインコンテンツ:**\n{script_main}")
                        if script_cta:
                            st.markdown(f"**📢 CTA:**\n{script_cta}")
                        if script_reason:
                            st.markdown(f"**✨ 効果的な理由:**\n{script_reason}")
                        st.caption(f"作成日: {script_created}")
                        
                        # 新規追加：編集ボタン
                        if st.button(f"✏️ 編集", key=f"edit_effective_{script_id}"):
                            st.session_state[f"edit_effective_{script_id}"] = True
                            st.rerun()
                        
                        # 新規追加：編集フォーム
                        if st.session_state.get(f"edit_effective_{script_id}", False):
                            with st.form(f"edit_effective_form_{script_id}"):
                                st.subheader(f"✏️ 台本編集: {script_title}")
                                
                                edit_title = st.text_input("📋 台本タイトル", value=script_title, key=f"edit_title_{script_id}")
                                edit_platform = st.selectbox("📱 プラットフォーム", 
                                                           ["TikTok", "Instagram Reels", "YouTube Shorts", "Meta"], 
                                                           index=["TikTok", "Instagram Reels", "YouTube Shorts", "Meta"].index(script_platform) if script_platform in ["TikTok", "Instagram Reels", "YouTube Shorts", "Meta"] else 0,
                                                           key=f"edit_platform_{script_id}")
                                edit_hook = st.text_area("🎣 フック", value=script_hook, key=f"edit_hook_{script_id}")
                                edit_main = st.text_area("💬 メインコンテンツ", value=script_main, key=f"edit_main_{script_id}")
                                edit_cta = st.text_area("📢 CTA", value=script_cta, key=f"edit_cta_{script_id}")
                                edit_reason = st.text_area("✨ 効果的な理由", value=script_reason, key=f"edit_reason_{script_id}")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.form_submit_button("💾 更新"):
                                        try:
                                            db.update_effective_script(script_id, edit_title, edit_hook, edit_main, edit_cta, edit_platform, edit_reason)
                                            st.success("✅ 効果的台本を更新しました！")
                                            st.session_state[f"edit_effective_{script_id}"] = False
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"❌ 更新中にエラーが発生しました: {str(e)}")
                                
                                with col2:
                                    if st.form_submit_button("❌ キャンセル"):
                                        st.session_state[f"edit_effective_{script_id}"] = False
                                        st.rerun()
            else:
                st.info("📝 効果的台本がまだ登録されていません")
        except Exception as e:
            st.error(f"❌ 効果的台本の取得中にエラーが発生しました: {str(e)}")
    
    with tab2:
        st.subheader("🤖 生成済み台本")
        
        try:
            # 生成済み台本の表示
            conn = db.get_connection()
            cursor = conn.cursor()
            if category_id:
                cursor.execute('''
                    SELECT gs.*, pc.category_name 
                    FROM generated_scripts gs
                    JOIN product_categories pc ON gs.category_id = pc.id
                    WHERE gs.category_id = ?
                    ORDER BY gs.created_at DESC
                ''', (category_id,))
            else:
                cursor.execute('''
                    SELECT gs.*, pc.category_name 
                    FROM generated_scripts gs
                    JOIN product_categories pc ON gs.category_id = pc.id
                    ORDER BY gs.created_at DESC
                ''')
            
            generated_scripts = cursor.fetchall()
            conn.close()
            
            if generated_scripts:
                for script in generated_scripts:
                    # データ構造を安全に取得
                    script_id = script[0] if len(script) > 0 else "不明"
                    script_title = script[2] if len(script) > 2 else "タイトル不明"
                    script_hook = script[3] if len(script) > 3 else ""
                    script_main = script[4] if len(script) > 4 else ""
                    script_cta = script[5] if len(script) > 5 else ""
                    script_platform = script[7] if len(script) > 7 else "プラットフォーム不明"
                    script_created = script[9] if len(script) > 9 else "作成日不明"
                    script_category = script[10] if len(script) > 10 else "カテゴリー不明"
                    
                    with st.expander(f"🤖 {script_title} ({script_platform} - {script_category})"):
                        if script_hook:
                            st.markdown(f"**🎣 フック:**\n{script_hook}")
                        if script_main:
                            st.markdown(f"**💬 メインコンテンツ:**\n{script_main}")
                        if script_cta:
                            st.markdown(f"**📢 CTA:**\n{script_cta}")
                        st.caption(f"作成日: {script_created}")
                        
                        # 配信結果入力ボタン
                        if st.button(f"📊 配信結果を入力", key=f"result_{script_id}"):
                            st.session_state[f"show_result_form_{script_id}"] = True
                        
                        # 配信結果入力フォーム
                        if st.session_state.get(f"show_result_form_{script_id}", False):
                            with st.form(f"result_form_{script_id}"):
                                st.write("📊 配信結果を入力してください")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    ctr = st.number_input("CTR (%)", min_value=0.0, step=0.01, key=f"ctr_{script_id}")
                                    cpc = st.number_input("CPC (円)", min_value=0.0, step=1.0, key=f"cpc_{script_id}")
                                    mcvr = st.number_input("mCVR (%)", min_value=0.0, step=0.01, key=f"mcvr_{script_id}")
                                
                                with col2:
                                    mcpa = st.number_input("mCPA (円)", min_value=0.0, step=1.0, key=f"mcpa_{script_id}")
                                    cvr = st.number_input("CVR (%)", min_value=0.0, step=0.01, key=f"cvr_{script_id}")
                                    cpa = st.number_input("CPA (円)", min_value=0.0, step=1.0, key=f"cpa_{script_id}")
                                
                                spend_amount = st.number_input("消化金額 (円)", min_value=0.0, step=1000.0, key=f"spend_{script_id}")
                                impressions = st.number_input("インプレッション数", min_value=0, step=1000, key=f"imp_{script_id}")
                                clicks = st.number_input("クリック数", min_value=0, step=100, key=f"click_{script_id}")
                                conversions = st.number_input("コンバージョン数", min_value=0, step=10, key=f"conv_{script_id}")
                                
                                col3, col4 = st.columns(2)
                                with col3:
                                    start_date = st.date_input("配信開始日", key=f"start_{script_id}")
                                with col4:
                                    end_date = st.date_input("配信終了日", key=f"end_{script_id}")
                                
                                if st.form_submit_button("📊 配信結果を保存"):
                                    try:
                                        results = {
                                            'ctr': ctr,
                                            'cpc': cpc,
                                            'mcvr': mcvr,
                                            'mcpa': mcpa,
                                            'cvr': cvr,
                                            'cpa': cpa,
                                            'spend_amount': spend_amount,
                                            'impressions': impressions,
                                            'clicks': clicks,
                                            'conversions': conversions,
                                            'start_date': start_date,
                                            'end_date': end_date
                                        }
                                        
                                        db.add_campaign_result(script_id, 'generated', script[1], script_platform, results)
                                        st.success("✅ 配信結果を保存しました！学習データが更新されました。")
                                        
                                        # 新規追加：入力フォームをクリア
                                        st.session_state[f"show_result_form_{script_id}"] = False
                                        clear_form_inputs()
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ 配信結果の保存中にエラーが発生しました: {str(e)}")
            else:
                st.info("🤖 生成済み台本がまだありません")
        except Exception as e:
            st.error(f"❌ 生成済み台本の取得中にエラーが発生しました: {str(e)}")
