---
name: Sub-Issue
about: A specific task that is part of a larger epic
title: '[SUB-ISSUE] '
labels: sub-issue
assignees: ''

---

## 背景とコンテキスト / Background and Context
<!-- このサブイシューが必要な理由と、エピック全体での位置づけを説明 -->
- **エピックの目的 / Epic Goal**: #[epic issue number] - [エピックのタイトル]
- **このタスクの役割 / Task Role**: 
- **ビジネス価値 / Business Value**: 

## 前提条件 / Prerequisites
<!-- このタスクを開始する前に必要なもの -->
- [ ] 必要な事前作業 / Required pre-work: 
  - [ ] #[issue number] - [説明]
- [ ] 必要な環境 / Required environment:
  - [ ] [開発環境、ツール、アクセス権限]
- [ ] 必要な知識 / Required knowledge:
  - [ ] [技術スタック、ドメイン知識]

## 依存関係 / Dependencies
<!-- 他のタスクとの関係性 -->
- **このタスクがブロックするもの / Blocks**: #[issue numbers]
- **このタスクをブロックするもの / Blocked by**: #[issue numbers]

## 成果物 / Deliverables
### 作成・修正するもの / What to create/modify
- [ ] `path/to/file1.py` - [説明]
- [ ] `path/to/file2.py` - [説明]
- [ ] `docs/feature.md` - [説明]

### 期待される動作 / Expected behavior
```
入力 / Input: [具体例]
出力 / Output: [期待される結果]
```

### エラーケース / Error cases
- [エラーケース1]: [対処方法]
- [エラーケース2]: [対処方法]

## 実装指針 / Implementation Guidelines
<!-- 既存コードとの整合性を保つための指針 -->
1. **ベースクラス/パターン**: [使用すべき既存のクラスやパターン]
2. **命名規則**: [プロジェクトの命名規則]
3. **エラーハンドリング**: [エラー処理のパターン]
4. **ログ出力**: [ログの出力方法]
5. **設定管理**: [設定の読み込み方法]

### コード例 / Code example
```python
# 既存のパターンに従った実装例
```

## テストと検証 / Testing and Validation
### ユニットテスト / Unit tests
```bash
# テストコマンド
pytest tests/test_feature.py -v
```

### 統合テスト / Integration tests
```bash
# 統合テストの実行方法
docker-compose up -d
python scripts/test_integration.py
```

### 動作確認手順 / Verification steps
1. [手順1]
2. [手順2]
3. [期待される結果]

## 完了の定義 / Definition of Done
- [ ] コードが実装されている / Code is implemented
- [ ] ユニットテストが書かれ、パスしている / Unit tests written and passing
- [ ] 統合テストがパスしている / Integration tests passing
- [ ] ドキュメントが更新されている / Documentation updated
- [ ] コードレビューが完了している / Code review completed
- [ ] CI/CDがグリーンである / CI/CD is green
- [ ] エピックの担当者に完了を報告した / Reported completion to epic owner

## 参考資料 / References
<!-- 関連するドキュメントやリソース -->
- [リンク1]
- [リンク2]

## 質問・不明点 / Questions
<!-- 不明な点があれば記載 -->