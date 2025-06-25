# RPi4 Interface Drivers 設計書

## 1. プロジェクト概要

### 1.1 目的
Raspberry Pi 4のハードウェアインターフェース（GPIO、I2C、SPI、UART）に対して、Dockerコンテナから透過的にアクセスし、受信した生データを他のコンテナへストリーミング配信するドライバーシステム。

### 1.2 主要機能
- ハードウェアインターフェースからの生データ取得
- 自動デバイス検出と接続管理
- 複数の配信方式によるデータストリーミング
- デバイス切断時の自動再接続
- OSSとして様々なシステムから利用可能

### 1.3 設計方針
- **透過性**: 生データをそのまま転送（プロトコル解釈なし）
- **拡張性**: 新しいインターフェースや配信方式の追加が容易
- **信頼性**: 自動再接続とエラーハンドリング
- **パフォーマンス**: 低レイテンシ、高スループット

## 2. システムアーキテクチャ（改訂版：権限分離モデル）

### 2.1 マイクロサービス構成

```
┌─────────────────────────────────────────────────────────┐
│                 Device Detector                         │
│                (privileged - 最小)                      │
│  ┌─────────────────────────────────────────────────┐    │
│  │ udev Event Monitor (~50行)                      │    │
│  │ - デバイス接続/切断検出のみ                         │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────┬───────────────────────────────────┘
                      │ Redis Events
┌─────────────────────▼───────────────────────────────────┐
│                Device Manager                           │
│                (標準権限)                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │VID/PID      │  │Device       │  │Config       │    │
│  │Database     │  │Profiles     │  │Generator    │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────┬───────────────────────────────────┘
                      │ Device Configs
┌─────────────────────▼───────────────────────────────────┐
│                Data Processor                           │
│                (標準権限)                                │
│  ┌─────────────┬─────────────┬─────────────┬──────┐    │
│  │GPIO Handler │I2C Handler  │SPI Handler  │UART  │    │
│  └─────────────┴─────────────┴─────────────┴──────┘    │
└─────────────────────┬───────────────────────────────────┘
                      │ Data Streams
              ┌───────┴───────┐
              │               │
        ┌─────▼─────┐   ┌─────▼─────┐
        │   MQTT    │   │ WebSocket │
        │  Broker   │   │  Server   │
        └───────────┘   └───────────┘
```

### 2.2 権限分離によるデータフロー

1. **Device Detector (privileged)**:
   - udevイベント監視（セキュリティに焦点を当てた最小実装）
   - デバイス接続/切断をRedisに通知
   - エラーハンドリングとサービス管理機能

2. **Device Manager (標準権限)**:
   - VID/PID識別とプロファイル適用
   - 設定生成とRedisに配信

3. **Data Processor (標準権限)**:
   - 実際のデバイス通信
   - データストリーミング配信

### 2.3 セキュリティ利点

- **最小攻撃対象領域**: privilegedコードを必要最小限に限定
- **障害分離**: サービス障害の波及を防止
- **監査容易性**: 明確に分離されたprivilegedコンポーネントの検証が簡単
- **実用性重視**: セキュリティと運用性のバランスを考慮

## 3. インターフェース仕様

### 3.1 GPIO
- **入力モード**: デジタル値の変化検出（エッジトリガー）
- **出力モード**: 外部からの制御コマンド受信（オプション）
- **割込み対応**: RISING/FALLING/BOTH エッジ検出

### 3.2 I2C
- **マスターモード**: 指定アドレスのデバイスからデータ読み取り
- **バス速度**: 100kHz/400kHz/1MHz
- **自動アドレススキャン**: 0x08-0x77の範囲

### 3.3 SPI
- **マスターモード**: フルデュプレックス通信
- **クロック速度**: 設定可能（最大50MHz）
- **CSピン管理**: 自動/手動選択可能

### 3.4 UART
- **ボーレート**: 9600-115200（自動検出可能）
- **データフォーマット**: 8N1（標準）、設定可能
- **フロー制御**: なし/ハードウェア/ソフトウェア

## 4. データ配信仕様

### 4.1 配信モード

#### Raw Only Mode
- 生データのみを配信
- 最小オーバーヘッド
- レガシーシステム互換

#### Tagged Mode（推奨）
- 8バイトのタイムスタンプ + 生データ
- バイナリ効率的
- ```[timestamp:8bytes][raw_data:n bytes]```

#### Structured Mode
- JSON形式でメタデータ付き
- デバッグ・解析向け
- ```json
  {
    "ts": 1736931234.567890,
    "interface": "uart",
    "device": "/dev/ttyS0",
    "raw": "base64_encoded_data"
  }
  ```

### 4.2 配信プロトコル

#### MQTT
- トピック構造: `{prefix}/{interface}/{device}/{channel}`
- QoS: 0（高速）/ 1（確実）
- ペイロード: 選択したモードに応じたフォーマット

#### WebSocket
- バイナリフレーム対応
- 自動再接続
- 複数クライアント同時接続

#### Redis Streams（オプション）
- 永続化対応
- 高速バッファリング

## 5. プラグアンドプレイ機能

### 5.1 リアルタイムデバイス検出
- **udevイベント監視**: デバイスの接続/切断を瞬時に検出
- **デバイス自動分類**: UART、I2C、SPI、GPIOの自動判別
- **ベンダー情報取得**: USB VID/PIDによるデバイス識別

### 5.2 ゼロ設定起動
```yaml
# 最小設定（完全自動モード）
version: 1
mode: auto
```

### 5.3 デバイスプロファイル
- **既知デバイス**: Arduino、FTDI、GPS等の自動認識
- **プロトコル推定**: 通信パターンによる自動プロトコル判定
- **最適設定**: デバイス固有のデフォルト設定適用

### 5.4 ホットプラグ対応
- **動的接続**: 実行中のデバイス追加/削除に対応
- **状態同期**: 定期的なデバイス状態確認
- **リアルタイム通知**: 接続状態変更の即座な通知

### 5.5 再接続ロジック
- Exponential Backoff: 1s → 2s → 4s → ... → 60s（最大）
- 接続状態の通知（イベント配信）
- エラー詳細のログ記録

## 6. 設定ファイル仕様

### 6.1 最小設定例
```yaml
# 完全自動モード（推奨）
version: 1
mode: auto

# または手動指定
version: 1
output:
  mode: tagged
  mqtt:
    broker: localhost
```

### 6.2 詳細設定例
```yaml
version: 1

# インターフェース設定
interfaces:
  uart:
    - device: /dev/ttyS0
      baudrate: 9600
      auto_reconnect: true
    - auto: true  # 自動検出
      
  i2c:
    - bus: 1
      address: 0x48
      poll_interval: 100  # ms
      
  spi:
    - bus: 0
      device: 0
      speed: 1000000
      
  gpio:
    - pins: [17, 27, 22]
      mode: input
      edge: both

# 出力設定
output:
  mode: tagged  # raw_only/tagged/structured
  
  mqtt:
    broker: mqtt-broker
    port: 1883
    qos: 0
    topic_prefix: "rpi4"
    
  websocket:
    port: 8080
    binary_mode: true

# 自動接続設定
auto_connection:
  enabled: true
  discovery:
    scan_interval: 5
  reconnection:
    initial_delay: 1
    max_delay: 60
    backoff_factor: 2

# ロギング
logging:
  level: INFO
  format: json
```

## 7. Docker設定

### 7.1 Dockerfile
```dockerfile
FROM python:3.11-slim

# 必要なシステムパッケージ
RUN apt-get update && apt-get install -y \
    i2c-tools \
    python3-smbus \
    && rm -rf /var/lib/apt/lists/*

# Pythonパッケージ
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーション
COPY src/ /app/src/
WORKDIR /app

CMD ["python", "-m", "src.main"]
```

### 7.2 docker-compose.yml
```yaml
version: '3.8'

services:
  rpi4-driver:
    build: .
    privileged: true  # プラグアンドプレイに必要
    volumes:
      - /dev:/dev
      - /sys:/sys:ro
      - /run/udev:/run/udev:ro  # udevイベント
      - ./config.yaml:/app/config.yaml
    environment:
      - LOG_LEVEL=INFO
      - HOTPLUG_MODE=enabled
      - AUTO_CONFIG=true
    restart: unless-stopped
    
  mqtt-broker:
    image: eclipse-mosquitto:latest
    ports:
      - "1883:1883"
    volumes:
      - ./mosquitto.conf:/mosquitto/config/mosquitto.conf
```

## 8. セキュリティ考慮事項

### 8.1 デバイスアクセス
- 最小権限の原則（必要なデバイスのみマッピング）
- privilegedモードの代替案検討

### 8.2 データ保護
- TLS/SSL対応（MQTT、WebSocket）
- 認証機能（オプション）

## 9. パフォーマンス目標

### 9.1 レイテンシ
- GPIO: < 1ms
- UART/I2C/SPI: < 5ms
- 配信遅延: < 10ms

### 9.2 スループット
- UART: 最大115200bps
- I2C: 最大1Mbps
- SPI: 最大10Mbps

### 9.3 リソース使用
- CPU: < 10%（アイドル時）
- メモリ: < 100MB
- ディスク: ログローテーション実装

## 10. テスト戦略

### 10.1 単体テスト
- 各インターフェースハンドラー
- 接続マネージャー
- データ配信機能

### 10.2 統合テスト
- 実デバイスとの接続テスト
- 自動再接続テスト
- 負荷テスト

### 10.3 モックモード
- ハードウェアなしでの動作確認
- CI/CD環境での自動テスト

## 11. 今後の拡張計画

### 11.1 追加インターフェース
- 1-Wire
- PWM
- ADC（アナログ入力）

### 11.2 追加配信方式
- gRPC
- Apache Kafka
- AMQP

### 11.3 高度な機能
- データフィルタリング（オプション）
- 圧縮転送
- バッチ配信モード