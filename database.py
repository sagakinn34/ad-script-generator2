import sqlite3
import os
from datetime import datetime
import json
import re

class DatabaseManager:
    def __init__(self, db_path='ad_script_database.db'):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """データベースとテーブルを初期化"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 1. 商材カテゴリー管理テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_name TEXT UNIQUE NOT NULL,
                target_ctr REAL DEFAULT 0.0,
                target_cpc REAL DEFAULT 0.0,
                target_mcvr REAL DEFAULT 0.0,
                target_mcpa REAL DEFAULT 0.0,
                target_cvr REAL DEFAULT 0.0,
                target_cpa REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 2. 効果的台本マスター（手動登録用）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS effective_scripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER,
                title TEXT NOT NULL,
                hook TEXT,
                main_content TEXT,
                call_to_action TEXT,
                script_content TEXT,
                platform TEXT,
                effectiveness_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES product_categories(id)
            )
        ''')
        
        # 3. 自動生成台本テーブル（既存scriptsを拡張）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS generated_scripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER,
                title TEXT,
                hook TEXT,
                main_content TEXT,
                call_to_action TEXT,
                script_content TEXT,
                platform TEXT,
                generation_source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES product_categories(id)
            )
        ''')
        
        # 4. 配信結果詳細テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS campaign_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                script_id INTEGER,
                script_type TEXT, -- 'effective' or 'generated'
                category_id INTEGER,
                platform TEXT,
                ctr REAL,
                cpc REAL,
                mcvr REAL,
                mcpa REAL,
                cvr REAL,
                cpa REAL,
                spend_amount REAL,
                impressions INTEGER,
                clicks INTEGER,
                conversions INTEGER,
                campaign_period_start DATE,
                campaign_period_end DATE,
                is_good_performance BOOLEAN,
                performance_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES product_categories(id)
            )
        ''')
        
        # 5. 学習パターンテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER,
                platform TEXT,
                pattern_type TEXT, -- 'numerical', 'keyword', 'structure', 'cta_pattern'
                pattern_content TEXT,
                effectiveness_score REAL,
                frequency_count INTEGER,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES product_categories(id)
            )
        ''')
        
        # 6. システム設定テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 7. API使用ログテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE,
                request_type TEXT,
                tokens_used INTEGER,
                cost_jpy REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 8. NGワード管理テーブル（新規追加）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ng_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER,
                word TEXT NOT NULL,
                word_type TEXT DEFAULT 'exact',
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES product_categories(id)
            )
        ''')
        
        # 9. プラットフォーム管理テーブル（新規追加）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS platforms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform_name TEXT UNIQUE NOT NULL,
                platform_code TEXT UNIQUE NOT NULL,
                description TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 初期プラットフォームデータの挿入
        cursor.execute('''
            INSERT OR IGNORE INTO platforms (platform_name, platform_code, description, sort_order)
            VALUES 
            ('TikTok', 'tiktok', 'TikTok向けショート動画', 1),
            ('Instagram Reels', 'instagram', 'Instagram Reels向けショート動画', 2),
            ('YouTube Shorts', 'youtube', 'YouTube Shorts向けショート動画', 3),
            ('Meta', 'meta', 'Meta（Facebook）向け動画', 4)
        ''')
        
        conn.commit()
        conn.close()
        print("✅ データベースが正常に初期化されました")
    
    # プラットフォーム管理メソッド（新規追加）
    def get_active_platforms(self):
        """アクティブなプラットフォーム一覧を取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT platform_name, platform_code, description 
            FROM platforms 
            WHERE is_active = TRUE 
            ORDER BY sort_order, platform_name
        ''')
        platforms = cursor.fetchall()
        conn.close()
        return platforms
    
    def get_all_platforms(self):
        """全てのプラットフォーム一覧を取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM platforms 
            ORDER BY sort_order, platform_name
        ''')
        platforms = cursor.fetchall()
        conn.close()
        return platforms
    
    def add_platform(self, platform_name, platform_code, description=None):
        """新しいプラットフォームを追加"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO platforms (platform_name, platform_code, description)
                VALUES (?, ?, ?)
            ''', (platform_name, platform_code, description))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()
    
    def update_platform(self, platform_id, platform_name, platform_code, description=None, is_active=True):
        """プラットフォームを更新"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE platforms SET
            platform_name = ?, platform_code = ?, description = ?, is_active = ?,
            updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (platform_name, platform_code, description, is_active, platform_id))
        conn.commit()
        conn.close()
    
    def delete_platform(self, platform_id):
        """プラットフォームを削除（論理削除）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE platforms SET is_active = FALSE WHERE id = ?', (platform_id,))
        conn.commit()
        conn.close()
    
    # 商材カテゴリー管理
    def add_product_category(self, category_name, targets=None):
        """商材カテゴリーを追加"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if targets:
                cursor.execute('''
                    INSERT INTO product_categories 
                    (category_name, target_ctr, target_cpc, target_mcvr, target_mcpa, target_cvr, target_cpa)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (category_name, targets.get('ctr', 0), targets.get('cpc', 0), 
                     targets.get('mcvr', 0), targets.get('mcpa', 0), 
                     targets.get('cvr', 0), targets.get('cpa', 0)))
            else:
                cursor.execute('INSERT INTO product_categories (category_name) VALUES (?)', (category_name,))
            
            conn.commit()
            category_id = cursor.lastrowid
            return category_id
        except sqlite3.IntegrityError:
            return None  # 既に存在する場合
        finally:
            conn.close()
    
    def get_product_categories(self):
        """商材カテゴリー一覧を取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM product_categories ORDER BY category_name')
        categories = cursor.fetchall()
        conn.close()
        return categories
    
    def update_category_targets(self, category_id, targets):
        """商材の目標値を更新"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE product_categories SET
            target_ctr = ?, target_cpc = ?, target_mcvr = ?, 
            target_mcpa = ?, target_cvr = ?, target_cpa = ?,
            updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (targets['ctr'], targets['cpc'], targets['mcvr'], 
              targets['mcpa'], targets['cvr'], targets['cpa'], category_id))
        conn.commit()
        conn.close()
    
    # 効果的台本管理
    def add_effective_script(self, category_id, title, hook, main_content, cta, platform, reason):
        """効果的台本を追加"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        script_content = f"【フック】\n{hook}\n\n【メイン】\n{main_content}\n\n【CTA】\n{cta}"
        
        cursor.execute('''
            INSERT INTO effective_scripts 
            (category_id, title, hook, main_content, call_to_action, script_content, platform, effectiveness_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (category_id, title, hook, main_content, cta, script_content, platform, reason))
        
        conn.commit()
        script_id = cursor.lastrowid
        conn.close()
        return script_id
    
    def get_effective_scripts(self, category_id=None, platform=None):
        """効果的台本を取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT es.*, pc.category_name 
            FROM effective_scripts es
            JOIN product_categories pc ON es.category_id = pc.id
            WHERE 1=1
        '''
        params = []
        
        if category_id:
            query += ' AND es.category_id = ?'
            params.append(category_id)
        
        if platform:
            query += ' AND es.platform = ?'
            params.append(platform)
        
        query += ' ORDER BY es.created_at DESC'
        
        cursor.execute(query, params)
        scripts = cursor.fetchall()
        conn.close()
        return scripts
    
    # 新規追加：効果的台本の取得（単一）
    def get_effective_script_by_id(self, script_id):
        """効果的台本を単一取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT es.*, pc.category_name 
            FROM effective_scripts es
            JOIN product_categories pc ON es.category_id = pc.id
            WHERE es.id = ?
        ''', (script_id,))
        
        script = cursor.fetchone()
        conn.close()
        return script
    
    # 新規追加：効果的台本の更新
    def update_effective_script(self, script_id, title, hook, main_content, cta, platform, reason):
        """効果的台本を更新"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        script_content = f"【フック】\n{hook}\n\n【メイン】\n{main_content}\n\n【CTA】\n{cta}"
        
        cursor.execute('''
            UPDATE effective_scripts SET
            title = ?, hook = ?, main_content = ?, call_to_action = ?, 
            script_content = ?, platform = ?, effectiveness_reason = ?,
            updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (title, hook, main_content, cta, script_content, platform, reason, script_id))
        
        conn.commit()
        conn.close()
    
    # 配信結果管理
    def add_campaign_result(self, script_id, script_type, category_id, platform, results):
        """配信結果を追加"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 目標値を取得
        cursor.execute('SELECT * FROM product_categories WHERE id = ?', (category_id,))
        targets = cursor.fetchone()
        
        if targets:
            # 良し悪し判定
            is_good = self._evaluate_performance(results, targets)
            performance_score = self._calculate_performance_score(results, targets)
        else:
            is_good = False
            performance_score = 0.0
        
        cursor.execute('''
            INSERT INTO campaign_results 
            (script_id, script_type, category_id, platform, ctr, cpc, mcvr, mcpa, cvr, cpa,
             spend_amount, impressions, clicks, conversions, campaign_period_start, 
             campaign_period_end, is_good_performance, performance_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (script_id, script_type, category_id, platform, 
              results['ctr'], results['cpc'], results['mcvr'], results['mcpa'], 
              results['cvr'], results['cpa'], results['spend_amount'],
              results['impressions'], results['clicks'], results['conversions'],
              results['start_date'], results['end_date'], is_good, performance_score))
        
        conn.commit()
        conn.close()
        
        # 学習パターン更新
        if is_good:
            self._update_learning_patterns(script_id, script_type, category_id, platform)
    
    def _evaluate_performance(self, results, targets):
        """配信結果の良し悪しを判定"""
        good_count = 0
        total_count = 0
        
        # 安全な数値比較をするための関数を作る
        def safe_compare_greater_equal(value, target):
            """数値を安全に比較する（以上かどうか）"""
            # 1. 値が空白かチェック
            if value is None or value == '' or value == 0:
                return False
            
            # 2. 目標値が設定されていないかチェック
            if target is None or target <= 0:
                return False
            
            # 3. 文字列を数値に変換して比較
            try:
                return float(value) >= float(target)
            except (ValueError, TypeError):
                # 数値に変換できない場合はFalse
                return False
        
        def safe_compare_less_equal(value, target):
            """数値を安全に比較する（以下かどうか）"""
            # 1. 値が空白かチェック
            if value is None or value == '' or value == 0:
                return False
            
            # 2. 目標値が設定されていないかチェック
            if target is None or target <= 0:
                return False
            
            # 3. 文字列を数値に変換して比較
            try:
                return float(value) <= float(target)
            except (ValueError, TypeError):
                # 数値に変換できない場合はFalse
                return False
        
        # CTR: 高いほど良い（安全な比較）
        if safe_compare_greater_equal(results.get('ctr'), targets[2]):
            good_count += 1
        total_count += 1
        
        # CPC: 低いほど良い（安全な比較）
        if safe_compare_less_equal(results.get('cpc'), targets[3]):
            good_count += 1
        total_count += 1
        
        # mCVR: 高いほど良い（安全な比較）
        if safe_compare_greater_equal(results.get('mcvr'), targets[4]):
            good_count += 1
        total_count += 1
        
        # mCPA: 低いほど良い（安全な比較）
        if safe_compare_less_equal(results.get('mcpa'), targets[5]):
            good_count += 1
        total_count += 1
        
        # CVR: 高いほど良い（安全な比較）
        if safe_compare_greater_equal(results.get('cvr'), targets[6]):
            good_count += 1
        total_count += 1
        
        # CPA: 低いほど良い（安全な比較）
        if safe_compare_less_equal(results.get('cpa'), targets[7]):
            good_count += 1
        total_count += 1
        
        return good_count / total_count >= 0.5  # 50%以上で良い判定
    
    def _calculate_performance_score(self, results, targets):
        """パフォーマンススコアを計算"""
        scores = []
        
        # 安全な割り算をするための関数を作る
        def safe_divide_and_score(value, target, is_lower_better=False):
            """安全に割り算してスコアを計算する"""
            # 1. 値が空白かチェック
            if value is None or value == '' or value == 0:
                return 0.0  # 空白なら0点
            
            # 2. 目標値が設定されていないかチェック
            if target is None or target <= 0:
                return 0.0
            
            # 3. 文字列を数値に変換して計算
            try:
                actual_value = float(value)
                target_value = float(target)
                
                if is_lower_better:
                    # CPCやCPAなど、低い方が良い指標の場合
                    if actual_value > 0:
                        ratio = target_value / actual_value
                    else:
                        return 0.0
                else:
                    # CTRやCVRなど、高い方が良い指標の場合
                    ratio = actual_value / target_value
                
                # 最大2倍までスコアを認める
                return min(ratio, 2.0)
                
            except (ValueError, TypeError, ZeroDivisionError):
                # 計算できない場合は0点
                return 0.0
        
        # 各指標のスコアを安全に計算
        if targets[2] > 0:  # CTR（高い方が良い）
            score = safe_divide_and_score(results.get('ctr'), targets[2], is_lower_better=False)
            scores.append(score)
        
        if targets[3] > 0:  # CPC（低い方が良い）
            score = safe_divide_and_score(results.get('cpc'), targets[3], is_lower_better=True)
            scores.append(score)
        
        if targets[4] > 0:  # mCVR（高い方が良い）
            score = safe_divide_and_score(results.get('mcvr'), targets[4], is_lower_better=False)
            scores.append(score)
        
        if targets[5] > 0:  # mCPA（低い方が良い）
            score = safe_divide_and_score(results.get('mcpa'), targets[5], is_lower_better=True)
            scores.append(score)
        
        if targets[6] > 0:  # CVR（高い方が良い）
            score = safe_divide_and_score(results.get('cvr'), targets[6], is_lower_better=False)
            scores.append(score)
        
        if targets[7] > 0:  # CPA（低い方が良い）
            score = safe_divide_and_score(results.get('cpa'), targets[7], is_lower_better=True)
            scores.append(score)
        
        # 平均スコアを計算（スコアがない場合は0.0）
        return sum(scores) / len(scores) if scores else 0.0
    
    def _update_learning_patterns(self, script_id, script_type, category_id, platform):
        """学習パターンを更新（強化学習の核心機能）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 台本データを取得
            if script_type == 'effective':
                cursor.execute('SELECT hook, main_content, call_to_action FROM effective_scripts WHERE id = ?', (script_id,))
            else:
                cursor.execute('SELECT hook, main_content, call_to_action FROM generated_scripts WHERE id = ?', (script_id,))
            
            script_data = cursor.fetchone()
            if not script_data:
                return
            
            hook, main_content, cta = script_data
            
            # 配信結果を取得
            cursor.execute('''
                SELECT is_good_performance, performance_score, spend_amount 
                FROM campaign_results 
                WHERE script_id = ? AND script_type = ?
                ORDER BY created_at DESC LIMIT 1
            ''', (script_id, script_type))
            
            result = cursor.fetchone()
            if not result:
                return
            
            is_good, score, spend_amount = result
            
            # 重み付けスコア計算（消化金額による重み付け）
            weight = min(spend_amount / 100000, 10.0)  # 10万円で1.0、最大10.0
            weighted_score = score * weight * (1.0 if is_good else -0.5)
            
            # パターン抽出と更新
            patterns = self._extract_patterns(hook, main_content, cta)
            
            for pattern_type, pattern_content in patterns:
                # 既存のパターンを検索
                cursor.execute('''
                    SELECT id, effectiveness_score, frequency_count 
                    FROM learning_patterns 
                    WHERE category_id = ? AND platform = ? AND pattern_type = ? AND pattern_content = ?
                ''', (category_id, platform, pattern_type, pattern_content))
                
                existing = cursor.fetchone()
                
                if existing:
                    # 既存パターンを更新
                    pattern_id, current_score, current_count = existing
                    new_score = (current_score * current_count + weighted_score) / (current_count + 1)
                    new_count = current_count + 1
                    
                    cursor.execute('''
                        UPDATE learning_patterns 
                        SET effectiveness_score = ?, frequency_count = ?, last_updated = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (new_score, new_count, pattern_id))
                else:
                    # 新規パターンを追加
                    cursor.execute('''
                        INSERT INTO learning_patterns 
                        (category_id, platform, pattern_type, pattern_content, effectiveness_score, frequency_count)
                        VALUES (?, ?, ?, ?, ?, 1)
                    ''', (category_id, platform, pattern_type, pattern_content, weighted_score))
            
            conn.commit()
            print(f"✅ 学習パターンを更新しました: {len(patterns)}件")
            
        except Exception as e:
            print(f"❌ 学習パターンの更新に失敗しました: {str(e)}")
        finally:
            conn.close()
    
    def _extract_patterns(self, hook, main_content, cta):
        """台本からパターンを抽出"""
        patterns = []
        
        # 数値パターンの抽出
        all_text = f"{hook or ''} {main_content or ''} {cta or ''}"
        numbers = re.findall(r'\d+[,\d]*[円％%万億千百十日時間秒分]', all_text)
        for num in numbers:
            patterns.append(('numerical', num))
        
        # キーワードパターンの抽出
        keywords = ['限定', '今なら', '今だけ', '無料', '特別', '初回', '送料無料', '返金保証', 
                   'プロデュース', '認定', '承認', '研究', '効果', '実証', '業界', '最安値']
        for keyword in keywords:
            if keyword in all_text:
                patterns.append(('keyword', keyword))
        
        # 文章構造パターンの抽出
        if hook:
            if '？' in hook or '?' in hook:
                patterns.append(('structure', 'question_hook'))
            
            if '！' in hook or '!' in hook:
                patterns.append(('structure', 'exclamation_hook'))
            
            # 数字で始まるフック
            if re.match(r'^\d+', hook):
                patterns.append(('structure', 'number_start_hook'))
        
        # CTAパターンの抽出
        if cta:
            if '今すぐ' in cta:
                patterns.append(('cta_pattern', 'immediate_action'))
            
            if 'チェック' in cta:
                patterns.append(('cta_pattern', 'check_action'))
            
            if '試し' in cta:
                patterns.append(('cta_pattern', 'trial_action'))
        
        return patterns
    
    def get_learning_patterns(self, category_id=None, platform=None, min_effectiveness=0.0):
        """学習パターンを取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT pattern_type, pattern_content, effectiveness_score, frequency_count
            FROM learning_patterns
            WHERE effectiveness_score >= ?
        '''
        params = [min_effectiveness]
        
        if category_id:
            query += ' AND category_id = ?'
            params.append(category_id)
        
        if platform:
            query += ' AND platform = ?'
            params.append(platform)
        
        query += ' ORDER BY effectiveness_score DESC, frequency_count DESC'
        
        cursor.execute(query, params)
        patterns = cursor.fetchall()
        conn.close()
        return patterns
    
    def get_learning_statistics(self, category_id=None):
        """学習統計情報を取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # パターン数統計
        query = '''
            SELECT pattern_type, COUNT(*) as count, AVG(effectiveness_score) as avg_score
            FROM learning_patterns
            WHERE 1=1
        '''
        params = []
        
        if category_id:
            query += ' AND category_id = ?'
            params.append(category_id)
        
        query += ' GROUP BY pattern_type ORDER BY avg_score DESC'
        
        cursor.execute(query, params)
        stats = cursor.fetchall()
        conn.close()
        
        return stats
    
    # NGワード管理メソッド（新規追加）
    def add_ng_word(self, category_id, word, word_type='exact', reason=None):
        """NGワードを追加"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO ng_words (category_id, word, word_type, reason)
                VALUES (?, ?, ?, ?)
            ''', (category_id, word, word_type, reason))
            
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()
    
    def get_ng_words(self, category_id=None):
        """NGワードを取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if category_id:
            cursor.execute('''
                SELECT nw.*, pc.category_name 
                FROM ng_words nw
                JOIN product_categories pc ON nw.category_id = pc.id
                WHERE nw.category_id = ?
                ORDER BY nw.created_at DESC
            ''', (category_id,))
        else:
            cursor.execute('''
                SELECT nw.*, pc.category_name 
                FROM ng_words nw
                JOIN product_categories pc ON nw.category_id = pc.id
                ORDER BY nw.created_at DESC
            ''')
        
        words = cursor.fetchall()
        conn.close()
        return words

    def delete_ng_word(self, word_id):
        """NGワードを削除"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM ng_words WHERE id = ?', (word_id,))
        conn.commit()
        conn.close()
    
    def check_ng_words(self, text, category_id):
        """テキストにNGワードが含まれているかチェック"""
        ng_words = self.get_ng_words(category_id)
        violations = []
        
        for word_data in ng_words:
            word = word_data[2]  # word column
            word_type = word_data[3]  # word_type column
            
            if word_type == 'exact':
                if word in text:
                    violations.append(word)
            elif word_type == 'partial':
                if word.lower() in text.lower():
                    violations.append(word)
            elif word_type == 'regex':
                import re
                if re.search(word, text):
                    violations.append(word)
        
        return violations

# データベース初期化とテスト
if __name__ == "__main__":
    print("=== 統合版DatabaseManagerテスト開始 ===")
    db = DatabaseManager()
    
    # 基本機能テスト
    print("✅ データベースが初期化されました")
    
    # プラットフォーム管理テスト
    print("\n=== プラットフォーム管理テスト ===")
    
    # アクティブなプラットフォーム取得
    active_platforms = db.get_active_platforms()
    print(f"✅ アクティブなプラットフォーム: {len(active_platforms)}件")
    for platform in active_platforms:
        print(f"  - {platform[0]} ({platform[1]})")
    
    # 新しいプラットフォーム追加テスト
    test_platform_id = db.add_platform("LINE VOOM", "line_voom", "LINE VOOM向けショート動画")
    if test_platform_id:
        print(f"✅ テスト用プラットフォーム追加成功: ID {test_platform_id}")
        
        # プラットフォーム更新テスト
        db.update_platform(test_platform_id, "LINE VOOM", "line_voom", "LINE VOOM向けショート動画（更新）", True)
        print("✅ プラットフォーム更新成功")
        
        # プラットフォーム削除テスト
        db.delete_platform(test_platform_id)
        print("✅ プラットフォーム削除成功")
    else:
        print("❌ テスト用プラットフォーム追加失敗")
    
    # 空白値処理テスト
    print("\n=== 空白値処理テスト ===")
    
    # テスト用の目標値（targets配列のインデックス対応）
    # [0, 1, CTR, CPC, mCVR, mCPA, CVR, CPA]
    test_targets = [0, 0, 2.0, 100, 1.0, 2000, 0.5, 3000]
    
    # テスト1: 正常な数値
    test_results1 = {
        'ctr': 2.5,
        'cpc': 80,
        'mcvr': 1.2,
        'mcpa': 1500,
        'cvr': 0.8,
        'cpa': 2500
    }
    
    print("テスト1（正常な数値）:")
    evaluation1 = db._evaluate_performance(test_results1, test_targets)
    score1 = db._calculate_performance_score(test_results1, test_targets)
    print(f"  評価結果: {evaluation1} ({'良い' if evaluation1 else '悪い'})")
    print(f"  スコア: {score1:.2f}")
    
    # テスト2: 空白値を含む
    test_results2 = {
        'ctr': 2.5,
        'cpc': '',      # 空文字列
        'mcvr': None,   # None
        'mcpa': 1500,
        'cvr': 'abc',   # 文字列
        'cpa': 0        # ゼロ
    }
    
    print("\nテスト2（空白値を含む）:")
    evaluation2 = db._evaluate_performance(test_results2, test_targets)
    score2 = db._calculate_performance_score(test_results2, test_targets)
    print(f"  評価結果: {evaluation2} ({'良い' if evaluation2 else '悪い'})")
    print(f"  スコア: {score2:.2f}")
    
    # テスト3: 全て空白
    test_results3 = {
        'ctr': '',
        'cpc': None,
        'mcvr': '',
        'mcpa': None,
        'cvr': '',
        'cpa': None
    }
    
    print("\nテスト3（全て空白）:")
    evaluation3 = db._evaluate_performance(test_results3, test_targets)
    score3 = db._calculate_performance_score(test_results3, test_targets)
    print(f"  評価結果: {evaluation3} ({'良い' if evaluation3 else '悪い'})")
    print(f"  スコア: {score3:.2f}")
    
    print("\n✅ 空白値処理のテストが完了しました！")
    print("エラーが発生しなければ修正成功です🎉")
    
    # 学習パターンテスト
    print("\n=== 学習パターンテスト ===")
    patterns = db.get_learning_patterns()
    print(f"現在の学習パターン数: {len(patterns)}")
    
    # 統計情報テスト
    stats = db.get_learning_statistics()
    print(f"パターン統計: {len(stats)}種類")
    
    for pattern_type, count, avg_score in stats:
        print(f"- {pattern_type}: {count}件, 平均スコア: {avg_score:.2f}")
    
    # NGワード機能テスト
    print("\n=== NGワード機能テスト ===")
    
    # テスト用カテゴリー作成
    test_category_id = db.add_product_category("テスト商材")
    if test_category_id:
        print(f"✅ テスト用カテゴリー作成成功: ID {test_category_id}")
        
        # NGワード追加テスト
        ng_word_id = db.add_ng_word(test_category_id, "絶対", "exact", "薬機法により使用禁止")
        if ng_word_id:
            print(f"✅ NGワード追加成功: ID {ng_word_id}")
            
            # NGワードチェックテスト
            test_text = "この商品は絶対に効果があります"
            violations = db.check_ng_words(test_text, test_category_id)
            if violations:
                print(f"✅ NGワードチェック成功: {violations}")
            else:
                print("❌ NGワードチェック失敗")
            
            # NGワード取得テスト
            ng_words = db.get_ng_words(test_category_id)
            print(f"✅ NGワード取得成功: {len(ng_words)}件")
            
            # NGワード削除テスト
            db.delete_ng_word(ng_word_id)
            print("✅ NGワード削除成功")
        else:
            print("❌ NGワード追加失敗")
    else:
        print("❌ テスト用カテゴリー作成失敗")
    
    print("\n✅ 統合版DatabaseManagerのテストが完了しました！")
