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

# プラットフォーム選択肢を取得する関数（新規追加）
@st.cache_data
def get_platform_options():
    """プラットフォーム選択肢を取得"""
    platforms = db.get_active_platforms()
    return [platform[0] for platform in platforms]  # platform_name のリスト

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
    
    # 台本生成フォーム（プラットフォーム選択を動的に変更）
    with st.form("script_generation_form"):
        st.subheader(f"📂 {category_name} の台本生成")
        
        col1, col2 = st.columns(2)
        
        with col1:
            target_audience = st.text_input("🎯 ターゲット層", placeholder="例：20-30代女性")
            platform_options = get_platform_options()
            platform = st.selectbox("📱 プラットフォーム", platform_options)
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
                    platform_options = get_platform_options()
                    platform = st.selectbox("📱 プラットフォーム", platform_options, key="form_effective_platform")
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
                    script_category = script[11] if len(script) > 11 else "カテゴリー不明"
                    
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
                                platform_options = get_platform_options()
                                platform_index = 0
                                if script_platform in platform_options:
                                    platform_index = platform_options.index(script_platform)
                                edit_platform = st.selectbox("📱 プラットフォーム", platform_options, index=platform_index, key=f"edit_platform_{script_id}")
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

elif page == "📊 成果管理":
    st.title("📊 成果管理")
    st.markdown("---")
    
    # フィルタリング機能を追加
    st.subheader("🔍 フィルター")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # カテゴリーフィルター
        categories = db.get_product_categories()
        category_filter_options = ["全て"] + [f"{cat[0]}: {cat[1]}" for cat in categories]
        selected_category_filter = st.selectbox("📂 カテゴリーフィルター", category_filter_options)
        
        if selected_category_filter == "全て":
            filter_category_id = None
        else:
            filter_category_id = int(selected_category_filter.split(":")[0])
    
    with col2:
        # プラットフォームフィルター（動的に変更）
        platform_filter_options = ["全て"] + get_platform_options()
        platform_filter = st.selectbox("📱 プラットフォーム", platform_filter_options)
        if platform_filter == "全て":
            platform_filter = None
    
    with col3:
        # 成果フィルター
        performance_filter = st.selectbox("📊 成果", ["全て", "良好のみ", "要改善のみ"])
    
    # 配信結果一覧（フィルタリング機能付き）
    st.subheader("📈 配信結果一覧")
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # SQLクエリを動的に構築
    query = '''
        SELECT cr.*, pc.category_name,
               CASE 
                   WHEN cr.script_type = 'effective' THEN es.title
                   WHEN cr.script_type = 'generated' THEN gs.title
                   ELSE 'タイトル不明'
               END as script_title
        FROM campaign_results cr
        JOIN product_categories pc ON cr.category_id = pc.id
        LEFT JOIN effective_scripts es ON cr.script_id = es.id AND cr.script_type = 'effective'
        LEFT JOIN generated_scripts gs ON cr.script_id = gs.id AND cr.script_type = 'generated'
        WHERE 1=1
    '''
    
    params = []
    
    # フィルター条件を追加
    if filter_category_id:
        query += ' AND cr.category_id = ?'
        params.append(filter_category_id)
    
    if platform_filter:
        query += ' AND cr.platform = ?'
        params.append(platform_filter)
    
    if performance_filter == "良好のみ":
        query += ' AND cr.is_good_performance = 1'
    elif performance_filter == "要改善のみ":
        query += ' AND cr.is_good_performance = 0'
    
    query += ' ORDER BY cr.created_at DESC'
    
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    
    if results:
        # 結果の統計情報を表示
        total_results = len(results)
        good_results = sum(1 for r in results if r[17])  # is_good_performance
        good_rate = (good_results / total_results * 100) if total_results > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("総結果数", f"{total_results}件")
        with col2:
            st.metric("良好な結果", f"{good_results}件")
        with col3:
            st.metric("良好率", f"{good_rate:.1f}%")
        
        st.markdown("---")
        
        # 結果詳細を表示
        for result in results:
            is_good = "✅ 良好" if result[17] else "❌ 要改善"
            performance_score = f"{result[18]:.2f}"
            
            with st.expander(f"{is_good} {result[20]} ({result[4]} - {result[19]}) - スコア: {performance_score}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("CTR", f"{result[5]:.2f}%")
                    st.metric("CPC", f"¥{result[6]:.0f}")
                
                with col2:
                    st.metric("mCVR", f"{result[7]:.2f}%")
                    st.metric("mCPA", f"¥{result[8]:.0f}")
                
                with col3:
                    st.metric("CVR", f"{result[9]:.2f}%")
                    st.metric("CPA", f"¥{result[10]:.0f}")
                
                col4, col5 = st.columns(2)
                with col4:
                    st.metric("消化金額", f"¥{result[11]:,.0f}")
                    st.metric("インプレッション", f"{result[12]:,}")
                
                with col5:
                    st.metric("クリック数", f"{result[13]:,}")
                    st.metric("コンバージョン数", f"{result[14]:,}")
                
                st.caption(f"配信期間: {result[15]} - {result[16]}")
    else:
        st.info("📊 フィルター条件に合致する配信結果がありません")
        
    st.markdown("---")
    st.info("💡 目標値の設定・編集は「⚙️ 設定」ページで行ってください")

elif page == "📈 レポート":
    st.title("📈 レポート")
    st.markdown("---")
    
    if not category_id:
        st.warning("⚠️ 商材カテゴリーを選択してください")
        st.stop()
    
    # 基本統計
    st.subheader("📊 基本統計")
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # 効果的台本数
    cursor.execute('SELECT COUNT(*) FROM effective_scripts WHERE category_id = ?', (category_id,))
    effective_count = cursor.fetchone()[0]

    # 生成済み台本数
    cursor.execute('SELECT COUNT(*) FROM generated_scripts WHERE category_id = ?', (category_id,))
    generated_count = cursor.fetchone()[0]
    
    # 配信結果数
    cursor.execute('SELECT COUNT(*) FROM campaign_results WHERE category_id = ?', (category_id,))
    result_count = cursor.fetchone()[0]
    
    # 良好な結果の割合
    cursor.execute('''
        SELECT COUNT(*) as good_count,
               (SELECT COUNT(*) FROM campaign_results WHERE category_id = ?) as total_count
        FROM campaign_results 
        WHERE category_id = ? AND is_good_performance = 1
    ''', (category_id, category_id))
    
    good_result = cursor.fetchone()
    good_rate = (good_result[0] / good_result[1] * 100) if good_result[1] > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("効果的台本", f"{effective_count}件")
    with col2:
        st.metric("生成済み台本", f"{generated_count}件")
    with col3:
        st.metric("配信結果", f"{result_count}件")
    with col4:
        st.metric("良好な結果", f"{good_rate:.1f}%")
    
    # 学習統計
    st.subheader("🤖 学習統計")
    
    stats = db.get_learning_statistics(category_id)
    if stats:
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**パターン種別統計**")
            for pattern_type, count, avg_score in stats:
                st.metric(f"{pattern_type}パターン", f"{count}件", f"平均スコア: {avg_score:.2f}")
        
        with col2:
            st.write("**効果的な学習パターン**")
            patterns = db.get_learning_patterns(category_id, min_effectiveness=0.5)
            if patterns:
                for pattern_type, content, score, frequency in patterns[:10]:
                    st.write(f"- {pattern_type}: {content} (スコア: {score:.2f}, 回数: {frequency})")
            else:
                st.info("効果的な学習パターンがまだありません")
    else:
        st.info("🤖 学習データがまだありません")
    
    # パフォーマンス推移
    st.subheader("📈 パフォーマンス推移")
    
    cursor.execute('''
        SELECT DATE(created_at) as date, 
               AVG(performance_score) as avg_score,
               COUNT(*) as count
        FROM campaign_results 
        WHERE category_id = ?
        GROUP BY DATE(created_at)
        ORDER BY date
    ''', (category_id,))
    
    performance_data = cursor.fetchall()
    
    if performance_data:
        df = pd.DataFrame(performance_data, columns=['日付', '平均スコア', '件数'])
        df['日付'] = pd.to_datetime(df['日付'])
        
        st.line_chart(df.set_index('日付')['平均スコア'])
        st.dataframe(df)
    else:
        st.info("📈 パフォーマンスデータがまだありません")
    
    conn.close()

elif page == "⚙️ 設定":
    st.title("⚙️ 設定")
    st.markdown("---")
    
    # タブで機能を分離（プラットフォーム管理タブを追加）
    tab1, tab2, tab3, tab4 = st.tabs(["📂 カテゴリー管理", "🎯 目標値設定", "🚫 NGワード管理", "📱 プラットフォーム管理"])
    
    with tab1:
        # 既存のカテゴリー管理機能（そのまま）
        st.subheader("📂 商材カテゴリー管理")
        
        # 新しいカテゴリー追加（既存コードをそのまま移動）
        with st.expander("➕ 新しい商材カテゴリーを追加"):
            # 既存のコードをそのまま使用
            with st.form("add_category"):
                category_name = st.text_input("📋 カテゴリー名", placeholder="例：ダイエット商品", key="form_category_name")
                
                st.write("🎯 初期目標値設定（後で変更可能）")
                col1, col2 = st.columns(2)
                
                with col1:
                    init_ctr = st.number_input("初期CTR目標 (%)", min_value=0.0, step=0.1, value=1.0, key="form_init_ctr")
                    init_cpc = st.number_input("初期CPC目標 (円)", min_value=0.0, step=10.0, value=100.0, key="form_init_cpc")
                    init_mcvr = st.number_input("初期mCVR目標 (%)", min_value=0.0, step=0.1, value=5.0, key="form_init_mcvr")
                
                with col2:
                    init_mcpa = st.number_input("初期mCPA目標 (円)", min_value=0.0, step=100.0, value=2000.0, key="form_init_mcpa")
                    init_cvr = st.number_input("初期CVR目標 (%)", min_value=0.0, step=0.1, value=2.0, key="form_init_cvr")
                    init_cpa = st.number_input("初期CPA目標 (円)", min_value=0.0, step=100.0, value=5000.0, key="form_init_cpa")
                
                if st.form_submit_button("📂 カテゴリーを追加"):
                    targets = {
                        'ctr': init_ctr,
                        'cpc': init_cpc,
                        'mcvr': init_mcvr,
                        'mcpa': init_mcpa,
                        'cvr': init_cvr,
                        'cpa': init_cpa
                    }
                    
                    category_id_new = db.add_product_category(category_name, targets)
                    if category_id_new:
                        st.success(f"✅ カテゴリー「{category_name}」を追加しました！")
                        
                        # 新規追加：入力フォームをクリア
                        clear_form_inputs()
                        st.rerun()
                    else:
                        st.error("❌ 同じ名前のカテゴリーが既に存在します")
        
        # 既存カテゴリー一覧（既存コードをそのまま移動）
        st.subheader("📋 既存カテゴリー一覧")
        
        categories = db.get_product_categories()
        if categories:
            for category in categories:
                with st.expander(f"📂 {category[1]} (ID: {category[0]})"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("目標CTR", f"{category[2]:.2f}%")
                        st.metric("目標CPC", f"¥{category[3]:.0f}")
                        st.metric("目標mCVR", f"{category[4]:.2f}%")
                    
                    with col2:
                        st.metric("目標mCPA", f"¥{category[5]:.0f}")
                        st.metric("目標CVR", f"{category[6]:.2f}%")
                        st.metric("目標CPA", f"¥{category[7]:.0f}")
                    
                    st.caption(f"作成日: {category[8]} | 更新日: {category[9]}")
        else:
            st.info("📂 カテゴリーがまだ登録されていません")
    
    with tab2:
        # 新規追加：目標値編集機能（成果管理から移動）
        st.subheader("🎯 目標値設定・編集")
        
        # カテゴリー選択（サイドバー以外でも選択可能）
        categories = db.get_product_categories()
        if categories:
            # カテゴリー選択ボックス
            category_options_local = [f"{cat[0]}: {cat[1]}" for cat in categories]
            selected_category_local = st.selectbox("📂 編集するカテゴリーを選択", category_options_local)
            
            if selected_category_local:
                selected_category_id = int(selected_category_local.split(":")[0])
                selected_category_name = selected_category_local.split(":")[1].strip()
                
                # 選択されたカテゴリーの現在の目標値を取得
                current_category = next((cat for cat in categories if cat[0] == selected_category_id), None)
                
                if current_category:
                    with st.form("target_settings_in_config"):
                        st.subheader(f"📂 {current_category[1]} の目標値編集")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            target_ctr = st.number_input("目標CTR (%)", value=float(current_category[2]), min_value=0.0, step=0.01, key="form_target_ctr")
                            target_cpc = st.number_input("目標CPC (円)", value=float(current_category[3]), min_value=0.0, step=1.0, key="form_target_cpc")
                            target_mcvr = st.number_input("目標mCVR (%)", value=float(current_category[4]), min_value=0.0, step=0.01, key="form_target_mcvr")
                        
                        with col2:
                            target_mcpa = st.number_input("目標mCPA (円)", value=float(current_category[5]), min_value=0.0, step=1.0, key="form_target_mcpa")
                            target_cvr = st.number_input("目標CVR (%)", value=float(current_category[6]), min_value=0.0, step=0.01, key="form_target_cvr")
                            target_cpa = st.number_input("目標CPA (円)", value=float(current_category[7]), min_value=0.0, step=1.0, key="form_target_cpa")
                        
                        if st.form_submit_button("💾 目標値を更新"):
                            targets = {
                                'ctr': target_ctr,
                                'cpc': target_cpc,
                                'mcvr': target_mcvr,
                                'mcpa': target_mcpa,
                                'cvr': target_cvr,
                                'cpa': target_cpa
                            }
                            db.update_category_targets(selected_category_id, targets)
                            st.success("✅ 目標値を更新しました！")
                            
                            # 新規追加：入力フォームをクリア
                            clear_form_inputs()
                            st.rerun()
        else:
            st.info("📂 まずカテゴリーを作成してください")
    
    with tab3:
        # 新規追加：NGワード管理機能
        st.subheader("🚫 NGワード管理")
        
        if not categories:
            st.warning("⚠️ まずカテゴリーを作成してください")
        else:
            # カテゴリー選択
            category_options_ng = [f"{cat[0]}: {cat[1]}" for cat in categories]
            selected_category_ng = st.selectbox("📂 NGワードを管理するカテゴリーを選択", category_options_ng, key="ng_category")
            
            if selected_category_ng:
                ng_category_id = int(selected_category_ng.split(":")[0])
                ng_category_name = selected_category_ng.split(":")[1].strip()
                
                # NGワード追加
                with st.expander("➕ NGワードを追加"):
                    with st.form("add_ng_word"):
                        st.subheader(f"📂 {ng_category_name} のNGワード追加")
                        
                        ng_word = st.text_input("🚫 NGワード", placeholder="例：絶対、必ず、100%", key="form_ng_word")
                        ng_word_type = st.selectbox("🔍 マッチタイプ", ["exact", "partial", "regex"], key="form_ng_word_type")
                        ng_reason = st.text_area("📝 理由", placeholder="例：薬機法により効果を断定する表現は使用禁止", key="form_ng_reason")
                        
                        st.info("""
                        **マッチタイプ説明:**
                        - **exact**: 完全一致（例：「絶対」のみ）
                        - **partial**: 部分一致（例：「絶対」を含む「絶対に」も対象）
                        - **regex**: 正規表現（例：「[0-9]+%」で数字+%パターン）
                        """)
                        
                        if st.form_submit_button("🚫 NGワードを追加"):
                            if ng_word:
                                try:
                                    word_id = db.add_ng_word(ng_category_id, ng_word, ng_word_type, ng_reason)
                                    if word_id:
                                        st.success(f"✅ NGワード「{ng_word}」を追加しました！")
                                        
                                        # 新規追加：入力フォームをクリア
                                        clear_form_inputs()
                                        st.rerun()
                                    else:
                                        st.error("❌ NGワードの追加に失敗しました")
                                except Exception as e:
                                    st.error(f"❌ エラーが発生しました: {str(e)}")
                            else:
                                st.error("❌ NGワードを入力してください")
                
                # 既存NGワード一覧
                st.subheader(f"📋 {ng_category_name} の登録済みNGワード")
                
                ng_words = db.get_ng_words(ng_category_id)
                if ng_words:
                    for ng_word in ng_words:
                        word_id = ng_word[0]
                        word = ng_word[2]
                        word_type = ng_word[3]
                        reason = ng_word[4] if ng_word[4] else "理由なし"
                        created_at = ng_word[5]
                        
                        with st.expander(f"🚫 {word} ({word_type})"):
                            st.write(f"**理由:** {reason}")
                            st.caption(f"作成日: {created_at}")
                            
                            if st.button(f"🗑️ 削除", key=f"delete_ng_{word_id}"):
                                try:
                                    db.delete_ng_word(word_id)
                                    st.success(f"✅ NGワード「{word}」を削除しました！")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ 削除中にエラーが発生しました: {str(e)}")
                else:
                    st.info("🚫 NGワードがまだ登録されていません")
                
                # NGワードテスト機能
                st.subheader("🧪 NGワードテスト")
                with st.expander("📝 テキストでNGワードをテスト"):
                    test_text = st.text_area("テストテキスト", placeholder="NGワードチェックしたいテキストを入力してください")
                    
                    if st.button("🔍 NGワードチェック"):
                        if test_text:
                            violations = db.check_ng_words(test_text, ng_category_id)
                            if violations:
                                st.error(f"❌ NGワードを検出しました: {', '.join(violations)}")
                            else:
                                st.success("✅ NGワードは検出されませんでした")
                        else:
                            st.warning("⚠️ テストテキストを入力してください")
    
    with tab4:
        # 新規追加：プラットフォーム管理機能
        st.subheader("📱 プラットフォーム管理")
        
        # 新しいプラットフォーム追加
        with st.expander("➕ 新しいプラットフォームを追加"):
            with st.form("add_platform"):
                platform_name = st.text_input("📱 プラットフォーム名", placeholder="例：LINE VOOM", key="form_platform_name")
                platform_code = st.text_input("🔑 プラットフォームコード", placeholder="例：line_voom", key="form_platform_code")
                description = st.text_area("📝 説明", placeholder="プラットフォームの特徴や用途", key="form_platform_description")
                
                if st.form_submit_button("📱 プラットフォームを追加"):
                    if platform_name and platform_code:
                        try:
                            platform_id = db.add_platform(platform_name, platform_code, description)
                            if platform_id:
                                st.success(f"✅ プラットフォーム「{platform_name}」を追加しました！")
                                
                                # 新規追加：入力フォームをクリア
                                clear_form_inputs()
                                st.rerun()
                            else:
                                st.error("❌ 同じ名前またはコードのプラットフォームが既に存在します")
                        except Exception as e:
                            st.error(f"❌ エラーが発生しました: {str(e)}")
                    else:
                        st.error("❌ プラットフォーム名とコードを入力してください")
        
        # 既存プラットフォーム管理
        st.subheader("📋 既存プラットフォーム管理")

        all_platforms = db.get_all_platforms()
        
        if all_platforms:
            for platform in all_platforms:
                platform_id = platform[0]
                platform_name = platform[1]
                platform_code = platform[2]
                description = platform[3]
                is_active = platform[4]
                
                status = "✅ アクティブ" if is_active else "❌ 非アクティブ"
                
                with st.expander(f"📱 {platform_name} ({status})"):
                    st.write(f"**コード:** {platform_code}")
                    if description:
                        st.write(f"**説明:** {description}")
                    
                    # 編集フォーム
                    with st.form(f"edit_platform_{platform_id}"):
                        edit_name = st.text_input("プラットフォーム名", value=platform_name, key=f"edit_name_{platform_id}")
                        edit_code = st.text_input("プラットフォームコード", value=platform_code, key=f"edit_code_{platform_id}")
                        edit_description = st.text_area("説明", value=description or "", key=f"edit_description_{platform_id}")
                        edit_active = st.checkbox("アクティブ", value=is_active, key=f"edit_active_{platform_id}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("💾 更新"):
                                try:
                                    db.update_platform(platform_id, edit_name, edit_code, edit_description, edit_active)
                                    st.success("✅ プラットフォームを更新しました！")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ 更新中にエラーが発生しました: {str(e)}")
                        
                        with col2:
                            if st.form_submit_button("🗑️ 削除"):
                                try:
                                    db.delete_platform(platform_id)
                                    st.success("✅ プラットフォームを削除しました！")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ 削除中にエラーが発生しました: {str(e)}")
        else:
            st.info("📱 プラットフォームがまだ登録されていません")
        
        # プラットフォーム使用状況
        st.subheader("📊 プラットフォーム使用状況")
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 効果的台本でのプラットフォーム使用状況
        cursor.execute('''
            SELECT platform, COUNT(*) as count 
            FROM effective_scripts 
            GROUP BY platform 
            ORDER BY count DESC
        ''')
        effective_platform_stats = cursor.fetchall()
        
        # 生成済み台本でのプラットフォーム使用状況
        cursor.execute('''
            SELECT platform, COUNT(*) as count 
            FROM generated_scripts 
            GROUP BY platform 
            ORDER BY count DESC
        ''')
        generated_platform_stats = cursor.fetchall()
        
        # 配信結果でのプラットフォーム使用状況
        cursor.execute('''
            SELECT platform, COUNT(*) as count 
            FROM campaign_results 
            GROUP BY platform 
            ORDER BY count DESC
        ''')
        campaign_platform_stats = cursor.fetchall()
        
        conn.close()
        
        if effective_platform_stats or generated_platform_stats or campaign_platform_stats:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write("**効果的台本**")
                for platform, count in effective_platform_stats:
                    st.write(f"- {platform}: {count}件")
            
            with col2:
                st.write("**生成済み台本**")
                for platform, count in generated_platform_stats:
                    st.write(f"- {platform}: {count}件")
            
            with col3:
                st.write("**配信結果**")
                for platform, count in campaign_platform_stats:
                    st.write(f"- {platform}: {count}件")
        else:
            st.info("📊 プラットフォーム使用データがまだありません")

# フッター
st.markdown("---")
st.markdown("🎬 **ショート動画台本自動生成ツール** | 統合AI学習システム + NGワード管理 + プラットフォーム管理")
