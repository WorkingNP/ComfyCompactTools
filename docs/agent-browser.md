# agent-browser クイックガイド

「使おうと思った時に一発で思い出す」ための最短メモです。

## AIに渡す指示テンプレ（コピー用）

```
あなたは agent-browser を使ってブラウザ操作を行う。
以下のルールを必ず守る。

- 使うのは agent-browser CLI のみ（可能なら --json 出力）。
- 許可URL/ドメイン: [ここに列挙]
  - 記載がないURLへは移動しない。必要ならユーザーに確認する。
- まず `open <url>` → `snapshot -i --json` を実行し、ref (@e1 など) を使って操作する。
- CSS セレクタは最終手段。基本は ref を使う。
- 画面遷移や DOM 変更の後は必ず再 `snapshot -i --json`。
- 待機が必要なら `wait <ms>` / `wait <selector>` を使う。
- 作業が終わったら `close`。

必要ならセッションを分離する:
- `--session <name>`

ログイン状態を維持したい場合:
- `--profile <path>` を使う
- もしくは `state save/load` で認証状態を保存・復元する
```

## 日本語の手順ガイド（5ステップ）

1. 事前準備（初回だけ）
   - `npx agent-browser install`
2. 開く
   - `npx agent-browser open https://example.com`
3. まずスナップショット
   - `npx agent-browser snapshot -i --json`
4. 操作（ref を使う）
   - `npx agent-browser click @e2`
   - `npx agent-browser fill @e3 "text"`
   - 画面が変わったら **再度** `snapshot -i --json`
5. 終了
   - `npx agent-browser close`

## よく使うコマンド

- `open <url>`: ページを開く
- `snapshot -i --json`: AI向けスナップショット（ref 付き）
- `click @eX` / `fill @eX "text"`: ref で操作
- `wait <ms>` / `wait <selector>`: 待機
- `get text @eX`: テキスト取得
- `screenshot [path]`: 画像保存
- `close`: 終了

## 覚えておくポイント

- URLの許可リスト機能は標準では無いので、必要なら「運用ルール」か「ラッパー」で制限する。
- 手順の自動保存（マクロ）は無い。必要ならコマンドをスクリプト化する。
- ログイン維持は `--profile` か `state save/load` が最短。
- うまく動かない時は `--headed` で可視化して様子を見る。
