# Pull Request Review Criteria / プルリクエストレビュー基準

## Overview
This document defines the mandatory criteria for PR approval in the RPi4 Interface Drivers project.

## 必須レビュー基準

### 1. 実機動作確認 (Real Device Verification) - ⭐最重要
すべてのPRは実機での動作確認を含む必要があります。

#### 必須提出物
- [ ] 実機での実行ログ（docker-compose logs）
- [ ] USBデバイス接続時のイベントログ
- [ ] ベアメタル vs Dockerコンテナの動作比較結果

#### 検証手順
```bash
# Step 1: 基本環境確認
docker-compose run --rm device-detector python3 -c "import pyudev; pyudev.Context()"

# Step 2: サービス起動とログ確認
docker-compose up -d
docker-compose logs -f device-detector

# Step 3: USBデバイス接続テスト
# USBデバイスを接続し、実際のイベントログを記録
```

### 2. テストカバレッジ (Test Coverage)
- [ ] ユニットテスト: 90%以上のカバレッジ
- [ ] 統合テスト: 主要なユースケースをカバー
- [ ] **実機テスト**: モックではない実環境でのテスト結果

### 3. セキュリティ要件 (Security Requirements)
- [ ] 特権コードは最小限（目標: 50行以下）
- [ ] 権限分離の原則を遵守
- [ ] セキュリティ監査ログの実装

### 4. ドキュメンテーション (Documentation)
- [ ] README.mdの更新
- [ ] アーキテクチャ図（変更がある場合）
- [ ] 実行例と期待される出力

### 5. Docker環境 (Docker Environment)
- [ ] Dockerfileのベストプラクティス準拠
- [ ] docker-compose.ymlの動作確認
- [ ] ヘルスチェックの実装

## レビュー評価レベル

### 🟢 承認 (Approved)
- すべての必須基準を満たしている
- 実機での動作が確認されている
- マイナーな改善提案のみ

### 🟡 条件付き承認 (Approved with conditions)
- 実機テスト以外の基準を満たしている
- 実機テストの計画と期限が明確
- 重大な問題がない

### 🔴 却下 (Changes requested)
- 実機での動作確認がない
- テストカバレッジが不十分
- セキュリティ上の懸念がある

## 実機検証の証拠として必要なもの

### 1. 環境情報
```bash
# ホスト環境
uname -a
lsb_release -a
docker --version

# RPi4のモデル情報
cat /proc/cpuinfo | grep Model
```

### 2. 実行ログ
```bash
# タイムスタンプ付きの完全なログ
docker-compose logs --timestamps device-detector > device-detector.log

# イベント受信の証拠
docker-compose logs --timestamps event-consumer > event-consumer.log
```

### 3. デバイス情報
```bash
# 接続前後のデバイスリスト
ls -la /dev/ttyUSB* /dev/ttyACM*
lsusb
dmesg | tail -20
```

## 例外事項
以下の場合のみ、実機検証を後回しにできます：
1. ドキュメントのみの変更
2. テストコードのみの変更（ただし、テスト自体は実機で実行すること）
3. 明確に実機に影響しないリファクタリング

## 実機がない場合の対応
1. GitHub Actionsでのハードウェアエミュレーション設定
2. 他の開発者による検証依頼
3. 検証用の環境構築手順の文書化

---

**重要**: 「動くはず」は「動いた」ではありません。実機での動作確認なしにマージすることは、プロジェクト全体のリスクとなります。