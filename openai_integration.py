import openai
import os
from datetime import datetime
import json
import sqlite3
from dotenv import load_dotenv
import re
from collections import Counter

load_dotenv()

class OpenAIIntegration:
    def __init__(self, db_path='ad_script_database.db'):
        self.db_path = db_path
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.client = None
        self.init_openai()
    
    def init_openai(self):
        """OpenAI APIクライアントを初期化"""
        if not self.api_key:
            print("❌ OpenAI API キーが設定されていません")
            return False
        
        try:
            self.client = openai.OpenAI(api_key=self.api_key)
            print("✅ OpenAI APIクライアントが正常に初期化されました")
            return True
        except Exception as e:
            print(f"❌ OpenAI APIクライアントの初期化に失敗しました: {str(e)}")
            return False
    
    def get_learning_data(self, category_id, platform):
        """学習データを取得（強化学習機能）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 学習パターンを取得
            cursor.execute('''
                SELECT pattern_type, pattern_content, effectiveness_score, frequency_count
                FROM learning_patterns
                WHERE category_id = ? AND platform = ? AND effectiveness_score > 0
                ORDER BY effectiveness_score DESC, frequency_count DESC
                LIMIT 20
            ''', (category_id, platform))
            
            positive_patterns = cursor.fetchall()
            
            # 悪い結果のパターンも取得
            cursor.execute('''
                SELECT pattern_type, pattern_content, effectiveness_score, frequency_count
                FROM learning_patterns
                WHERE category_id = ? AND platform = ? AND effectiveness_score < 0
                ORDER BY effectiveness_score ASC
                LIMIT 10
            ''', (category_id, platform))
            
            negative_patterns = cursor.fetchall()
            
            return {
                'positive_patterns': positive_patterns,
                'negative_patterns': negative_patterns
            }
        
        except Exception as e:
            print(f"❌ 学習データの取得に失敗しました: {str(e)}")
            return {'positive_patterns': [], 'negative_patterns': []}
        
        finally:
            conn.close()
    
    def analyze_effective_scripts(self, reference_scripts):
        """効果的台本を分析して共通パターンを抽出"""
        if not reference_scripts:
            return {}
        
        analysis = {
            'numerical_patterns': [],
            'authority_patterns': [],
            'urgency_patterns': [],
            'hook_starters': [],
            'cta_patterns': [],
            'frequent_keywords': [],
            'benefit_patterns': []
        }
        
        all_hooks = []
        all_mains = []
        all_ctas = []
        
        for script in reference_scripts:
            if len(script) > 3 and script[3]:
                all_hooks.append(script[3])
            if len(script) > 4 and script[4]:
                all_mains.append(script[4])
            if len(script) > 5 and script[5]:
                all_ctas.append(script[5])
        
        all_text = ' '.join(all_hooks + all_mains + all_ctas)
        
        # 数値パターンの抽出
        numbers = re.findall(r'\d+[,\d]*[円％%万億千百十]', all_text)
        analysis['numerical_patterns'] = list(set(numbers))
        
        # 権威性パターンの抽出
        authority_keywords = ['プロデュース', 'ハーバード', '大学', '研究', '博士', '医師', '専門家', '認定', '承認', '特許']
        for keyword in authority_keywords:
            if keyword in all_text:
                analysis['authority_patterns'].append(keyword)
        
        # 緊急性パターンの抽出
        urgency_keywords = ['今なら', '限定', '今だけ', '期間限定', '数量限定', '今すぐ', '1度しか', '残り', '最後']
        for keyword in urgency_keywords:
            if keyword in all_text:
                analysis['urgency_patterns'].append(keyword)
        
        # フック開始パターンの抽出
        hook_starters = []
        for hook in all_hooks:
            starter = hook[:10] if len(hook) > 10 else hook
            hook_starters.append(starter)
        analysis['hook_starters'] = hook_starters
        
        # CTAパターンの抽出
        cta_patterns = []
        for cta in all_ctas:
            if 'チェック' in cta:
                cta_patterns.append('チェック')
            if '試して' in cta:
                cta_patterns.append('試して')
            if '無料' in cta:
                cta_patterns.append('無料')
        analysis['cta_patterns'] = list(set(cta_patterns))
        
        # 頻出キーワードの抽出
        words = re.findall(r'[一-龯ぁ-ゔァ-ヴー]+', all_text)
        word_counts = Counter(words)
        analysis['frequent_keywords'] = [word for word, count in word_counts.most_common(15) 
                                       if len(word) > 1 and count > 1]
        
        return analysis
    
    def create_integrated_prompt(self, category, target_audience, platform, 
                               script_length, reference_scripts=None, category_id=None):
        """統合版プロンプト作成（効果的台本 + 強化学習、トーン削除）"""
        
        # 1. 効果的台本の分析（40%の重み）
        manual_analysis = self.analyze_effective_scripts(reference_scripts)
        
        # 2. 強化学習データの取得（60%の重み）
        learning_data = self.get_learning_data(category_id, platform) if category_id else {'positive_patterns': [], 'negative_patterns': []}
        
        # 参考台本の詳細
        reference_details = ""
        if reference_scripts:
            reference_details = "\n\n【効果的台本（専門家選定）- 重み40%】\n"
            for i, script in enumerate(reference_scripts[:2], 1):
                script_title = script[2] if len(script) > 2 else "タイトル不明"
                script_hook = script[3] if len(script) > 3 else ""
                script_main = script[4] if len(script) > 4 else ""
                script_cta = script[5] if len(script) > 5 else ""
                script_reason = script[8] if len(script) > 8 else ""
                
                reference_details += f"""
効果的台本{i}: {script_title}
フック: {script_hook}
メイン: {script_main}
CTA: {script_cta}
効果的な理由: {script_reason}
"""
        
        # 強化学習データの指示
        learning_instructions = ""
        if learning_data['positive_patterns']:
            learning_instructions += "\n\n【強化学習データ（配信結果分析）- 重み60%】\n"
            learning_instructions += "🎯 実際の配信結果で効果が確認されたパターン（必ず活用）:\n"
            
            for pattern_type, content, score, count in learning_data['positive_patterns'][:10]:
                learning_instructions += f"- {pattern_type}: {content} (効果スコア: {score:.2f}, 出現回数: {count})\n"
        
        if learning_data['negative_patterns']:
            learning_instructions += "\n⚠️ 配信結果で効果が低かったパターン（避けてください）:\n"
            for pattern_type, content, score, count in learning_data['negative_patterns'][:5]:
                learning_instructions += f"- {pattern_type}: {content} (効果スコア: {score:.2f})\n"
        
        # 手動分析の指示
        manual_instructions = ""
        if manual_analysis:
            manual_instructions = f"""
【効果的台本の分析結果】
🔢 数値パターン: {', '.join(manual_analysis['numerical_patterns'][:5])}
🏆 権威性パターン: {', '.join(manual_analysis['authority_patterns'][:3])}
⚡ 緊急性パターン: {', '.join(manual_analysis['urgency_patterns'][:3])}
🎯 頻出キーワード: {', '.join(manual_analysis['frequent_keywords'][:8])}
"""
        
        prompt = f"""
あなたは{category}の広告台本を作成する超一流のコピーライターです。
効果的台本の専門家分析と実際の配信結果データを統合して、最高品質の台本を作成してください。

【基本条件】
- 商材カテゴリー: {category}
- ターゲット層: {target_audience}
- プラットフォーム: {platform}
- 台本の長さ: {script_length}

{reference_details}

{learning_instructions}

{manual_instructions}

【統合作成指示】
1. 強化学習データ（60%重み）を最優先で活用
   - 実際の配信結果で効果が確認されたパターンを必ず含める
   - 効果が低かったパターンは絶対に避ける

2. 効果的台本の分析結果（40%重み）も活用
   - 専門家が選定した成功パターンを参考にする
   - 具体的な数字、権威性、緊急性を含める

3. 両方のデータを統合して最適化
   - 学習データの高スコアパターンを効果的台本の成功要素と組み合わせる
   - ターゲット層に最も響く組み合わせを選択

【必須要素】
✅ 実際の配信結果で効果が確認された要素
✅ 具体的な数字（価格、効果、期間）
✅ 権威性を示す要素
✅ 緊急性を演出する要素
✅ リスク回避要素

【台本構成の詳細要求】
✅ フック: 
- 具体的な数字で始める
- 権威性や話題性を含める
- 3-5秒で注意を引く強力な訴求

✅ メインコンテンツ:
- 商品の具体的な効果・特徴
- 数値による裏付け
- 権威性の証明
- ターゲットのベネフィット

✅ CTA:
- 緊急性のある行動喚起
- 具体的な特典や割引
- リスク回避要素
- 行動を促す明確な指示

【出力形式】
以下のJSON形式で、データドリブンな最適台本を作成してください：

{{
    "title": "統合分析に基づく最適台本タイトル",
    "hook": "学習データ + 効果的台本の統合フック",
    "main_content": "配信結果で実証された効果的なメインコンテンツ",
    "call_to_action": "高いコンバージョンが実証されたCTA",
    "script_content": "完全な統合台本テキスト"
}}

重要: 配信結果の学習データを60%、効果的台本の分析を40%の重みで統合し、実際の成果に基づいた台本を作成してください。
"""
        
        return prompt
    
    def generate_script(self, category, target_audience, platform, script_length, reference_scripts=None, category_id=None):
        """
        統合版台本生成（効果的台本 + 強化学習、トーン削除、NGワードチェック）
        要件1対応：自動生成台本のみNGワードチェック適用
        """
        if not self.client:
            raise Exception("OpenAI APIクライアントが初期化されていません")
        
        try:
            # 統合プロンプトを作成
            prompt = self.create_integrated_prompt(
                category, target_audience, platform, 
                script_length, reference_scripts, category_id
            )
            
            # 要件1対応：自動生成台本にのみNGワード指示を追加
            ng_words_instruction = ""
            if category_id:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT word, reason FROM ng_words WHERE category_id = ?', (category_id,))
                ng_words = cursor.fetchall()
                conn.close()
                
                if ng_words:
                    ng_words_instruction = f"""
                    
【重要：レギュレーション（使用禁止ワード）】
以下の言葉は法的・レギュレーション上の理由により使用を禁止されています。
台本作成時は絶対に使用しないでください：

禁止ワード:
{chr(10).join([f"- {word} {f'（理由：{reason}）' if reason else ''}" for word, reason in ng_words])}

これらの言葉を使用せずに、効果的で魅力的な台本を作成してください。
"""
            
            # プロンプトにNGワード指示を追加
            prompt += ng_words_instruction
            
            # OpenAI APIで台本生成
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "あなたは効果的な広告台本作成の専門家です。レギュレーション遵守を最優先に、実際の配信結果データと専門家の分析を統合して、最高品質の台本を作成することが得意です。データドリブンなアプローチで、実証された成功パターンを活用してください。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1200
            )
            
            # レスポンスを解析
            response_text = response.choices[0].message.content
            
            # JSONの抽出と解析
            try:
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx != -1 and end_idx != -1:
                    json_str = response_text[start_idx:end_idx]
                    script_data = json.loads(json_str)
                else:
                    raise json.JSONDecodeError("JSON形式が見つかりません", response_text, 0)
                
            except json.JSONDecodeError:
                # フォールバック処理
                script_data = {
                    "title": f"{category}の統合分析台本",
                    "hook": "効果実証済みの強力なフック",
                    "main_content": "配信結果とエキスパート分析を統合したメインコンテンツ",
                    "call_to_action": "高コンバージョンが実証されたCTA",
                    "script_content": response_text
                }
            
            # 必要なフィールドの確認
            required_fields = ['title', 'hook', 'main_content', 'call_to_action']
            for field in required_fields:
                if field not in script_data:
                    script_data[field] = f"統合分析による{field}"
            
            # script_contentの作成
            if not script_data.get('script_content'):
                script_data['script_content'] = f"""🎣 フック: {script_data['hook']}

💬 メインコンテンツ: {script_data['main_content']}

📢 CTA: {script_data['call_to_action']}"""
            
            # 要件1対応：自動生成台本のみNGワードチェック・クリーン
            if category_id:
                cleaned_script, violations = self.check_and_clean_script(script_data, category_id)
                if violations:
                    print(f"⚠️ NGワードを検出・除去しました: {violations}")
                    script_data = cleaned_script
            
            # API使用ログを記録
            self.log_api_usage(
                request_type='integrated_script_generation',
                tokens_used=response.usage.total_tokens,
                cost_jpy=self.calculate_cost(response.usage.total_tokens)
            )
            
            return script_data
            
        except Exception as e:
            print(f"❌ 統合台本生成中にエラーが発生しました: {str(e)}")
            raise e
    
    def check_and_clean_script(self, script_data, category_id):
        """生成された台本のNGワードをチェック・除去"""
        if not category_id:
            return script_data, []
        
        # データベースからNGワードを取得
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT word, word_type FROM ng_words WHERE category_id = ?', (category_id,))
        ng_words = cursor.fetchall()
        conn.close()
        
        if not ng_words:
            return script_data, []
        
        violations = []
        cleaned_script = script_data.copy()
        
        # 各フィールドをチェック・クリーン
        for field in ['title', 'hook', 'main_content', 'call_to_action', 'script_content']:
            if field in cleaned_script and cleaned_script[field]:
                original_text = cleaned_script[field]
                cleaned_text = original_text
                
                for word, word_type in ng_words:
                    if word_type == 'exact':
                        if word in cleaned_text:
                            violations.append(word)
                            cleaned_text = cleaned_text.replace(word, '[規制対象]')
                    elif word_type == 'partial':
                        if word.lower() in cleaned_text.lower():
                            violations.append(word)
                            # 大文字小文字を考慮した置換
                            import re
                            cleaned_text = re.sub(re.escape(word), '[規制対象]', cleaned_text, flags=re.IGNORECASE)
                    elif word_type == 'regex':
                        import re
                        if re.search(word, cleaned_text):
                            violations.append(word)
                            cleaned_text = re.sub(word, '[規制対象]', cleaned_text)
                
                cleaned_script[field] = cleaned_text
        
        return cleaned_script, violations
    
    def calculate_cost(self, tokens):
        """トークン数から費用を計算（GPT-4o-mini）"""
        # GPT-4o-miniの料金: 入力 $0.00015/1K tokens, 出力 $0.0006/1K tokens
        # 簡単のため平均として $0.0003/1K tokens = 0.045円/1K tokens（150円/ドル換算）
        cost_per_1k_tokens = 0.045
        return (tokens / 1000) * cost_per_1k_tokens
    
    def log_api_usage(self, request_type, tokens_used, cost_jpy):
        """API使用ログを記録"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO api_usage_log (date, request_type, tokens_used, cost_jpy, created_at)
                VALUES (DATE('now'), ?, ?, ?, DATETIME('now'))
            ''', (request_type, tokens_used, cost_jpy))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"❌ API使用ログの記録に失敗しました: {str(e)}")
    
    def get_daily_usage(self):
        """当日のAPI使用量を取得"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) as request_count, 
                       SUM(tokens_used) as total_tokens,
                       SUM(cost_jpy) as total_cost
                FROM api_usage_log 
                WHERE date = DATE('now')
            ''')
            
            result = cursor.fetchone()
            conn.close()
            
            return {
                'request_count': result[0] or 0,
                'total_tokens': result[1] or 0,
                'total_cost': result[2] or 0.0
            }
            
        except Exception as e:
            print(f"❌ 使用量の取得に失敗しました: {str(e)}")
            return {'request_count': 0, 'total_tokens': 0, 'total_cost': 0.0}
    
    def check_daily_limit(self):
        """日次制限をチェック"""
        usage = self.get_daily_usage()
        
        # 日次制限の設定
        daily_request_limit = 100
        daily_cost_limit = 500.0  # 500円
        
        if usage['request_count'] >= daily_request_limit:
            return False, f"日次リクエスト制限({daily_request_limit}回)に達しました"
        
        if usage['total_cost'] >= daily_cost_limit:
            return False, f"日次コスト制限(¥{daily_cost_limit})に達しました"
        
        return True, "制限内です"
    
    def analyze_generated_script(self, script_data):
        """生成された台本の品質を分析"""
        analysis = {
            'has_numbers': False,
            'has_urgency': False,
            'has_authority': False,
            'hook_strength': 0,
            'cta_strength': 0,
            'overall_score': 0
        }
        
        script_text = f"{script_data.get('hook', '')} {script_data.get('main_content', '')} {script_data.get('call_to_action', '')}"
        
        # 数値の有無
        if re.search(r'\d+[,\d]*[円％%万億千百十]', script_text):
            analysis['has_numbers'] = True
        
        # 緊急性の有無
        urgency_words = ['今なら', '限定', '今だけ', '今すぐ', '期間限定']
        if any(word in script_text for word in urgency_words):
            analysis['has_urgency'] = True
        
        # 権威性の有無
        authority_words = ['プロデュース', '認定', '研究', '専門家', '効果']
        if any(word in script_text for word in authority_words):
            analysis['has_authority'] = True
        
        # フック強度（簡単な評価）
        hook = script_data.get('hook', '')
        if hook:
            hook_score = 0
            if re.match(r'^\d+', hook):  # 数字で始まる
                hook_score += 2
            if '？' in hook or '?' in hook:  # 疑問文
                hook_score += 1
            if '！' in hook or '!' in hook:  # 感嘆符
                hook_score += 1
            analysis['hook_strength'] = hook_score
        
        # CTA強度
        cta = script_data.get('call_to_action', '')
        if cta:
            cta_score = 0
            if '今すぐ' in cta:
                cta_score += 2
            if '無料' in cta:
                cta_score += 1
            if 'チェック' in cta:
                cta_score += 1
            analysis['cta_strength'] = cta_score
        
        # 総合スコア
        overall_score = 0
        if analysis['has_numbers']:
            overall_score += 2
        if analysis['has_urgency']:
            overall_score += 2
        if analysis['has_authority']:
            overall_score += 2
        overall_score += analysis['hook_strength']
        overall_score += analysis['cta_strength']
        
        analysis['overall_score'] = overall_score
        
        return analysis

# テスト実行
if __name__ == "__main__":
    print("=== 統合版OpenAI統合テスト開始 ===")
    
    # .envファイルの確認
    if os.path.exists('.env'):
        print("✅ .envファイルが見つかりました")
    else:
        print("❌ .envファイルが見つかりません")
        exit(1)
    
    # OpenAI統合の初期化
    openai_service = OpenAIIntegration()
    
    if openai_service.client:
        print("✅ OpenAI APIクライアントが正常に初期化されました")
        
        # データベースの確認
        try:
            conn = sqlite3.connect('ad_script_database.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            conn.close()
            print("✅ データベースが正常に確認されました")
            
            # 簡単なテスト生成
            print("\n=== 統合版台本生成テスト ===")
            test_script = openai_service.generate_script(
                category="健康サプリメント",
                target_audience="30-50代男性",
                platform="TikTok",
                script_length="30秒",
                reference_scripts=None,
                category_id=1
            )
            
            print("✅ 統合版台本生成成功！")
            print(f"タイトル: {test_script['title']}")
            print(f"フック: {test_script['hook']}")
            print(f"メイン: {test_script['main_content'][:100]}...")
            print(f"CTA: {test_script['call_to_action']}")
            
            # 台本品質分析テスト
            print("\n=== 台本品質分析テスト ===")
            analysis = openai_service.analyze_generated_script(test_script)
            print(f"数値含有: {analysis['has_numbers']}")
            print(f"緊急性含有: {analysis['has_urgency']}")
            print(f"権威性含有: {analysis['has_authority']}")
            print(f"フック強度: {analysis['hook_strength']}")
            print(f"CTA強度: {analysis['cta_strength']}")
            print(f"総合スコア: {analysis['overall_score']}")
            
            # NGワード機能テスト
            print("\n=== NGワード機能テスト ===")
            test_script_with_ng = {
                "title": "絶対に効果がある商品",
                "hook": "この商品は絶対に効果があります",
                "main_content": "100%の効果を保証します",
                "call_to_action": "今すぐ購入してください",
                "script_content": "絶対に効果がある商品です"
            }
            
            cleaned_script, violations = openai_service.check_and_clean_script(test_script_with_ng, 1)
            if violations:
                print(f"✅ NGワード検出・除去成功: {violations}")
                print(f"クリーン後タイトル: {cleaned_script['title']}")
            else:
                print("ℹ️ NGワードが検出されませんでした（NGワードが未登録の場合）")
            
        except Exception as e:
            print(f"❌ テスト中にエラーが発生しました: {str(e)}")
    else:
        print("❌ OpenAI APIクライアントの初期化に失敗しました")
    
    print("\n✅ 統合版OpenAI統合のテストが完了しました！")
