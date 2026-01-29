# UI改善プラン - SDXL Workflow & Gallery

## 概要
SDXLワークフロー選択時のUIに関する4つの問題を修正します。

---

## 問題1: チェックポイント/VAE選択フィールドが編集不可

### 現状
- SDXLワークフローのmanifest.jsonで`checkpoint`と`vae`が`string`型として定義されている
- `choices`配列が設定されていないため、`generateDynamicForm()`が`<input type="text">`を生成
- ユーザーはファイル名を手入力する必要があり、ローカルにあるcheckpoint/vaeを選択できない

### 原因
- `workflows/sdxl_txt2img/manifest.json`に`choices`配列が未定義
- または、サーバー側の`/api/config`エンドポイントから取得した選択肢をdynamic formに渡していない

### 解決策（2つのアプローチから選択）

#### アプローチA: manifest.jsonに直接choices配列を追加
```json
"checkpoint": {
  "type": "string",
  "choices": [
    "sd_xl_base_1.0.safetensors",
    "juggernautXL_v9.safetensors",
    "animagineXLV3_v30.safetensors"
  ],
  "default": "sd_xl_base_1.0.safetensors",
  "patch": {"node_id": "1", "field": "inputs.ckpt_name"}
}
```
**利点**: シンプル、ワークフロー固有のモデルリストを定義可能
**欠点**: ローカルに追加したモデルを反映するにはmanifest編集が必要

#### アプローチB: サーバーAPIから動的取得（推奨）
1. `/api/config`から`checkpoint_choices`と`vae_choices`を取得（既存機能）
2. `generateDynamicForm()`関数を修正：
   - `param.type === "string"`でも、param名が`checkpoint`または`vae`の場合
   - グローバル変数`state.config`からchoicesを注入
3. `<select>`タグを動的生成

**実装箇所**: `web/app.js`の`generateDynamicForm()`関数（448-534行）

```javascript
// web/app.js内 generateDynamicForm()の修正例
if (paramSchema.choices && paramSchema.choices.length > 0) {
  // 既存のchoices処理
  const sel = document.createElement('select');
  // ...
} else if (paramSchema.type === 'string' &&
           (paramName === 'checkpoint' || paramName === 'vae') &&
           state.config) {
  // 新規追加: checkpointとvaeの動的選択肢注入
  const sel = document.createElement('select');
  const choices = paramName === 'checkpoint'
    ? state.config.checkpoint_choices
    : state.config.vae_choices;
  choices.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c;
    opt.textContent = c;
    if (c === paramSchema.default) opt.selected = true;
    sel.appendChild(opt);
  });
  sel.id = paramName;
  sel.dataset.paramName = paramName;
  sel.dataset.paramType = 'string';
  inputEl = sel;
}
```

### 実装タスク
1. `web/app.js`の`generateDynamicForm()`を修正（上記コード）
2. `workflows/sdxl_txt2img/manifest.json`と`workflows/flux2_txt2img/manifest.json`で
   - `checkpoint`と`vae`パラメータに`"ui_type": "model_select"`などのメタデータを追加（将来拡張用）
3. テスト: SDXLワークフロー選択時にcheckpoint/vaeがドロップダウンで表示されることを確認

---

## 問題2: パラメータレイアウトが不適切

### 現状
- `grid2`クラスで2カラムレイアウト
- 左列: generation, cfg_scale, height, sampler, seed, vae
- 右列: generate button, checkpoint, negative_prompt, noise_scheduler, steps, width
- 論理的なグルーピングがなく、関連フィールド（width/height、prompt/negative_prompt）が分散

### 問題点
1. widthとheightが左右に分かれている（本来は隣接すべき）
2. promptとnegative_promptが左右に分かれている
3. 視覚的に走査しづらく、入力効率が悪い

### 解決策: セクション別レイアウト

#### 新しいレイアウト構造
```
┌─ Prompts Section ────────────────────┐
│ ┌─ Prompt ──────────────────────┐   │
│ │ (textarea, full width)        │   │
│ └───────────────────────────────┘   │
│ ┌─ Negative Prompt ─────────────┐   │
│ │ (textarea, full width)        │   │
│ └───────────────────────────────┘   │
└──────────────────────────────────────┘

┌─ Image Settings ─────────────────────┐
│ Width [1024▼]  Height [1024▼]       │
│ Checkpoint [sd_xl_base_1.0.safe...▼]│
│ VAE [sdxl_vae.safetensors▼]         │
└──────────────────────────────────────┘

┌─ Sampling Settings ──────────────────┐
│ Steps [30]      CFG Scale [7.5]      │
│ Sampler [dpmpp▼] Scheduler [karras▼]│
│ Seed [-1]       Batch [1]            │
└──────────────────────────────────────┘

[Generate Button]
```

### 実装タスク
1. `web/app.js`の`generateDynamicForm()`を修正：
   - パラメータをカテゴリ別に分類（prompt系、image系、sampling系）
   - セクション別に`<fieldset>`または`<div class="param-section">`で囲む
   - 各セクションに`<legend>`または`<h3>`でタイトル追加

2. `web/styles.css`に新しいスタイル追加：
```css
.param-section {
  margin-bottom: 16px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--bg-secondary, #1a1a1a);
}

.param-section h3 {
  margin: 0 0 8px 0;
  font-size: 0.9em;
  color: var(--text-secondary);
  text-transform: uppercase;
}

.param-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.param-full-width {
  grid-column: 1 / -1;
}
```

3. パラメータ分類ロジック例：
```javascript
const paramCategories = {
  prompts: ['prompt', 'negative_prompt'],
  image: ['width', 'height', 'checkpoint', 'vae'],
  sampling: ['steps', 'cfg_scale', 'sampler', 'scheduler', 'seed', 'batch']
};
```

---

## 問題3: 画像サイズ入力が1ずつしか変動しない

### 現状
- `<input type="number" step="1">`のため、上下矢印で1ずつしか増減できない
- 512→1024への変更に512回クリックが必要（非現実的）

### 解決策: サイズプリセットボタン + 手入力

#### UI設計
```
Width:  [⚡512] [⚡768] [⚡1024] [⚡1536] [📝Custom: 1024]
Height: [⚡512] [⚡768] [⚡1024] [⚡1536] [📝Custom: 1024]
```

#### 実装方法

##### 方法A: ボタングループ + 入力フィールド（推奨）
```html
<label>Width</label>
<div class="size-preset-group">
  <button type="button" class="preset-btn" data-target="width" data-value="512">512</button>
  <button type="button" class="preset-btn" data-target="width" data-value="768">768</button>
  <button type="button" class="preset-btn" data-target="width" data-value="1024">1024</button>
  <button type="button" class="preset-btn" data-target="width" data-value="1536">1536</button>
  <input type="number" id="width" min="512" max="2048" step="64" value="1024">
</div>
```

##### 方法B: select + custom入力切り替え
```html
<select id="width-preset" onchange="applyPreset('width', this.value)">
  <option value="512">512px</option>
  <option value="768">768px</option>
  <option value="1024" selected>1024px</option>
  <option value="1536">1536px</option>
  <option value="custom">Custom...</option>
</select>
<input type="number" id="width-custom" style="display:none" min="512" max="2048" step="8">
```

### 実装タスク
1. `web/app.js`の`generateDynamicForm()`を修正：
   - `paramName === 'width' || paramName === 'height'`の場合
   - プリセットボタングループ + 入力フィールドのHTMLを生成
   - 共通プリセット値: `[512, 768, 1024, 1280, 1536, 2048]`

2. イベントリスナー追加：
```javascript
function setupSizePresets() {
  document.querySelectorAll('.preset-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const target = e.target.dataset.target;
      const value = e.target.dataset.value;
      document.getElementById(target).value = value;
    });
  });
}
```

3. CSS追加：
```css
.size-preset-group {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.preset-btn {
  padding: 4px 8px;
  font-size: 0.85em;
  border: 1px solid var(--border);
  background: var(--bg-secondary);
  cursor: pointer;
  border-radius: 3px;
}

.preset-btn:hover {
  background: var(--accent);
}

.size-preset-group input[type="number"] {
  flex: 1;
  min-width: 80px;
}
```

---

## 問題4: 画像ギャラリーが崩壊

### 現状
- 生成画像が増えると、すべてがgrid表示され、スクロールが長大になる
- 個々のサムネイルが小さくなり、視認性が低下
- ページ読み込みが遅くなる（lazy loadingはあるが限界）

### 解決策: タブ形式 + ページネーション

#### UI設計
```
┌─ Gallery ─────────────────────────────┐
│ [← Prev] Page 1/5 [Next →]            │
│ ┌───┬───┬───┐                         │
│ │   │   │   │ (3x3 grid, 9 images)   │
│ ├───┼───┼───┤                         │
│ │   │   │   │                         │
│ ├───┼───┼───┤                         │
│ │   │   │   │                         │
│ └───┴───┴───┘                         │
│                                        │
│ Thumbnail Size: [────●────] 200px     │
└────────────────────────────────────────┘
```

### 実装タスク

#### 1. `web/app.js`に`GalleryPagination`クラス追加
```javascript
class GalleryPagination {
  constructor(itemsPerPage = 9) {
    this.itemsPerPage = itemsPerPage;
    this.currentPage = 1;
  }

  getTotalPages(assets) {
    return Math.ceil(assets.size / this.itemsPerPage);
  }

  getPageItems(assets, page) {
    const start = (page - 1) * this.itemsPerPage;
    const end = start + this.itemsPerPage;
    return Array.from(assets.values()).slice(start, end);
  }

  render(assets, container) {
    const totalPages = this.getTotalPages(assets);
    const pageItems = this.getPageItems(assets, this.currentPage);

    // Clear existing content
    container.innerHTML = '';

    // Render pagination controls
    const controls = document.createElement('div');
    controls.className = 'gallery-pagination-controls';
    controls.innerHTML = `
      <button id="prevPage" ${this.currentPage === 1 ? 'disabled' : ''}>← Prev</button>
      <span>Page ${this.currentPage} / ${totalPages}</span>
      <button id="nextPage" ${this.currentPage === totalPages ? 'disabled' : ''}>Next →</button>
    `;
    container.appendChild(controls);

    // Render grid
    const grid = document.createElement('div');
    grid.className = 'gallery-grid-paginated';
    pageItems.forEach(asset => {
      const card = this.createCard(asset);
      grid.appendChild(card);
    });
    container.appendChild(grid);

    // Attach event listeners
    document.getElementById('prevPage')?.addEventListener('click', () => {
      if (this.currentPage > 1) {
        this.currentPage--;
        this.render(assets, container);
      }
    });

    document.getElementById('nextPage')?.addEventListener('click', () => {
      if (this.currentPage < totalPages) {
        this.currentPage++;
        this.render(assets, container);
      }
    });
  }

  createCard(asset) {
    // 既存のrenderGallery()のcard生成ロジックを再利用
    const card = document.createElement('div');
    card.className = 'card';
    // ... (既存のカード生成コード)
    return card;
  }
}
```

#### 2. `web/app.js`の`renderGallery()`を修正
```javascript
// グローバル変数に追加
const galleryPaginator = new GalleryPagination(9);

function renderGallery() {
  const g = document.getElementById('gallery');
  if (!g) return;

  // ページネーション版レンダリング
  galleryPaginator.render(state.assets, g);
}
```

#### 3. `web/styles.css`に追加
```css
.gallery-pagination-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border);
}

.gallery-pagination-controls button {
  padding: 6px 12px;
  background: var(--accent);
  border: none;
  border-radius: 4px;
  cursor: pointer;
  color: white;
}

.gallery-pagination-controls button:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.gallery-grid-paginated {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  padding: 12px;
  min-height: 600px; /* 固定高さでレイアウトシフト防止 */
}

@media (max-width: 1200px) {
  .gallery-grid-paginated {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .gallery-grid-paginated {
    grid-template-columns: 1fr;
  }
}
```

#### 4. オプション: キーボードショートカット追加
```javascript
// web/app.js内
document.addEventListener('keydown', (e) => {
  if (e.key === 'ArrowLeft' && galleryPaginator.currentPage > 1) {
    galleryPaginator.currentPage--;
    renderGallery();
  } else if (e.key === 'ArrowRight' &&
             galleryPaginator.currentPage < galleryPaginator.getTotalPages(state.assets)) {
    galleryPaginator.currentPage++;
    renderGallery();
  }
});
```

---

## 実装優先順位

### Phase 1: クリティカル修正（必須）
1. ✅ チェックポイント/VAE選択フィールドの修正（問題1）
2. ✅ 画像ギャラリーのページネーション実装（問題4）

### Phase 2: UX改善（推奨）
3. ✅ パラメータレイアウトの再構成（問題2）
4. ✅ 画像サイズプリセットボタン追加（問題3）

### Phase 3: 追加最適化（オプション）
- サムネイルサイズのプリセット（小/中/大ボタン）
- ギャラリーのソート機能（新しい順/古い順/お気に入り）
- ワークフローごとのパラメータプリセット保存

---

## テスト計画

### 手動テスト項目
- [ ] SDXLワークフロー選択時、checkpointとvaeがドロップダウンで表示される
- [ ] ドロップダウンに実際のcheckpointファイル（C:\Users\souto\Desktop\ComfyUI_windows_portable\ComfyUI\models\checkpoints）が表示される
- [ ] widthとheightが隣接して配置されている
- [ ] promptとnegative_promptが隣接して配置されている
- [ ] 画像サイズプリセットボタン（512/768/1024など）が機能する
- [ ] ギャラリーが1ページ9枚で表示される
- [ ] ページネーションボタン（Prev/Next）が機能する
- [ ] 10枚以上画像を生成して、2ページ目に遷移できる
- [ ] ブラウザをリロードしても現在のページが保持される（localStorage使用時）

### 自動テスト（オプション）
- JavaScript unit test for `generateDynamicForm()` with checkpoint/vae parameters
- CSS visual regression test for layout changes
- Integration test: submit job with new form layout

---

## リスクと対策

### リスク1: 既存のレガシーフォームとの競合
- **対策**: `if (state.selectedWorkflow)` 分岐で新しいレイアウトを適用、レガシーモードは従来通り

### リスク2: checkpoint/vae選択肢の動的読み込み失敗
- **対策**: `/api/config`が失敗した場合、manifest.jsonのchoicesにフォールバック

### リスク3: ページネーション実装でWebSocketの新規画像追加が反映されない
- **対策**: `ws.onmessage`で`asset_new`受信時、currentPageが最初のページの場合のみ自動でrenderGallery()を呼ぶ

### リスク4: 大量の画像資産でメモリ消費増加
- **対策**: 仮想スクロール（virtual scrolling）は今回見送り、ページネーションで十分対応可能

---

## 完了条件

1. ✅ SDXLワークフロー選択時、checkpointとvaeのドロップダウンが表示される
2. ✅ パラメータが論理的にグルーピングされている（Prompts/Image Settings/Sampling Settings）
3. ✅ 画像サイズ変更がプリセットボタンで1クリックで可能
4. ✅ ギャラリーが1ページ9枚表示で、ページネーションが機能する
5. ✅ 既存の画像生成機能（prompt入力、generate実行、WebSocket更新）が正常動作する
6. ✅ レガシーフォーム（ワークフロー未選択時）が従来通り動作する

---

## 次のステップ

1. このプランについてユーザーに確認
2. 承認後、Phase 1から順次実装開始
3. 各Phase完了後、スクリーンショットで動作確認
4. すべての修正完了後、統合テストとドキュメント更新
