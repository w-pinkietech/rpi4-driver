# RPi4 Interface Drivers Project

## 🚨 最重要：Git チェックポイント戦略
**すべての変更作業で必須**：細かなコミットで常に安全な状態を保つ

### 必須実行タイミング
- ファイル変更前：`git commit -m "checkpoint: before modifying [filename]"`
- 機能追加後：`git commit -m "checkpoint: added [feature] - working"`
- テスト通過後：`git commit -m "checkpoint: tests passing"`
- エラー解決後：`git commit -m "checkpoint: fixed [issue]"`
- **作業中断前：必ずコミット**

## 🌿 ブランチ戦略
### ブランチ命名規則（必須）
```
feature/issue-{番号}-{簡潔な説明}  # 新機能
fix/issue-{番号}-{簡潔な説明}      # バグ修正
test/issue-{番号}-{簡潔な説明}     # テスト追加
docs/issue-{番号}-{簡潔な説明}     # ドキュメント
refactor/{簡潔な説明}              # リファクタリング
```

### 開発フロー
1. `git checkout main && git pull origin main`
2. `git checkout -b feature/issue-42-add-i2c-scan`
3. 開発とチェックポイントコミット
4. `git push origin feature/issue-42-add-i2c-scan`
5. PR作成とレビュー

## 🔄 初期化：作業開始時の必須確認
**すべての会話の最初に実行**：現状把握のための初期化

### 必須確認項目
1. **現在のブランチ名を確認**：`git branch --show-current`
2. **関連Issue番号の特定**：ブランチ名から推測
3. **対応するPRの存在確認**：GitHubで該当PRを検索
4. **作業進捗の把握**：Issue/PRのコメントや状態を確認

この初期化により、適切な作業継続や新規作業開始を判断する。

## 📋 プロジェクト概要
Raspberry Pi 4のインターフェース（GPIO、I2C、SPI、UART）をDockerコンテナから監視・アクセスするためのドライバープロジェクト。

### 開発要件
- Raspberry Pi 4
- Docker and Docker Compose
- Python 3.11+
- Access to /dev devices from Docker containers

## 🔧 テストコマンド
```bash
# Run tests
python -m pytest tests/

# Lint code
python -m flake8 src/

# Type check
python -m mypy src/
```

## 📚 ドキュメント参照ガイド

### 作業内容に応じた参照先
- **設計・アーキテクチャ**: `docs/design/`
- **開発プロセス**: `docs/process/`
  - 開発ルール: `DEVELOPMENT_RULES.md`
  - PRガイドライン: `PR_GUIDELINES.md`
  - Claude連携: `CLAUDE_COLLABORATION.md`
- **Issue/PR作成時**:
  - Issue Templates: `.github/ISSUE_TEMPLATE/`
  - PR Template: `.github/pull_request_template.md`

## 🐳 Docker設定
必要なデバイスマッピング:
- GPIO: /dev/gpiomem
- I2C: /dev/i2c-*
- SPI: /dev/spidev*
- UART: /dev/ttyAMA0, /dev/ttyS0