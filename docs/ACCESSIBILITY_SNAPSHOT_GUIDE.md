# Accessibility Snapshot 功能指南

## 概述

AAT 现在使用 Playwright 的 **Accessibility Snapshot** 来收集页面元素，替代了之前的纯 DOM 查询方式。这种方式自动过滤装饰性元素，提供更可靠的元素定位。

## 为什么使用 Accessibility Snapshot

### 传统 DOM 查询的问题

**之前的实现**：使用 JavaScript `document.querySelectorAll()` 收集所有 DOM 元素
```javascript
// 收集所有元素，包括装饰性的
document.querySelectorAll('a, button, svg, ...')

// 问题：
// - 包含 footer 链接
// - 包含 logo SVG 图标
// - 包含导航图标
// - selector 太通用：`selector: "svg"` 匹配页面上所有 SVG
```

**案例**：Bing 搜索按钮
```html
<!-- 正确的按钮 -->
<label id="search_icon">
  <svg class="search icon"></svg>
</label>

<!-- 问题：SVG 图标也被收集，且有通用 selector "svg" -->
<svg class="logo">...</svg>
```

### Accessibility Snapshot 的优势

**新的实现**：使用 `page.accessibility.snapshot(interestingOnly=True)`
```python
# 只收集对用户有意义的交互元素
snapshot = await page.accessibility.snapshot(interestingOnly=True)

# 优势：
✅ 自动过滤装饰性元素（footer、logo、纯图标）
✅ 提供语义化角色（button, textbox, link）
✅ 唯一引用（e5, e10, e20）
✅ 用户视角的标签（"textbox 'What needs...'" 而不是 `<input>`）
```

## 数据结构变化

### scan_result.json 新字段

```json
{
  "elements": [
    {
      "label": "搜索",
      "type": "accessibility",
      "role": "textbox",
      "snapshot_ref": "e5",
      "accessible_name": "输入搜索词",
      "selector": "#sb_form_q",
      "source": "accessibility",
      "x": 630,
      "y": 170
    }
  ]
}
```

**新增字段**：
- `snapshot_ref`: Playwright 快照引用（e5, e10 等）
- `accessible_name`: 无障碍树中的名称
- `source`: `"accessibility"` （新增来源类型）
- `type`: `"accessibility"` （特殊类型标记）

### 场景 YAML 新字段

```yaml
- step: 3
  action: find_and_click
  target:
    snapshot_ref: "e5"    # 新增：最高优先级
    role: "button"        # 新增：角色验证
    text: "搜索"         # 保留：fallback
    selector: "#..."    # 保留：fallback
```

## 定位优先级

### Executor 定位链（从高到低）

```
1. Snapshot reference (e5)        ← 新增！最可靠
   ↓ 失效或不存在
2. CSS selector (#search_icon)  ← 现有
   ↓ 失效
3. Enhanced input field finding    ← 现有
   ↓ 失效
4. find_text_position             ← 现有
   ↓ 失效
5. 3-tier matching (OCR → Template → Vision AI) ← 现有
```

### 场景生成匹配优先级

```
1. Accessibility source + role      ← 新增！最可靠
   ↓ 匹配失败
2. Semantics source + role         ← 现有
   ↓ 匹配失败
3. DOM source + semantic selector ← 现有
   ↓ 匹配失败
4. OCR source                      ← 现有
```

## 使用示例

### 纯 Accessibility Snapshot

```bash
# Bing 搜索案例 - 自动过滤装饰元素
aat devqa "Type 'AI NEWS' in search box then click search button" \
  --url https://www.bing.com.cn

# 输出：
# ✅ 收集到 12 个元素（footer、logo 被自动过滤）
# ✅ 搜索框识别为：role="textbox", snapshot_ref="e5"
# ✅ 搜索按钮识别为：role="button", snapshot_ref="e6"
# ✅ 生成步骤使用 snapshot_ref 而不是通用 selector
```

### 混合模式（Accessibility + DOM + OCR）

```javascript
// 页面结构：
<div class="custom-button" onclick="submit()">Custom</div>

// Snapshot：✅ 识别为交互元素
// DOM：✅ 作为回退保留（某些自定义组件可能没有 ARIA）
// OCR：✅ 纯 Canvas 元素
```

## Snapshot Ref 的生命周期

### Ref 何时有效？

- ✅ **同一页面内**：ref 在单次快照内稳定（e5, e10, e20）
- ❌ **页面变更后**：导航、动态内容会导致 ref 失效
- ❌ **不同快照间**：每次 scan 生成新的 ref 编号

### 失效后的处理

**自动回退**：如果 snapshot_ref 失效，Executor 自动回退到：
1. CSS selector
2. 文本匹配（find_text_position）
3. OCR/Vision AI

**重新扫描**：如果 ref 频繁失效，建议：
```bash
# 在每次页面变更后重新 scan
aat scan --url https://example.com
```

## 调试技巧

### 查看 Snapshot 元素

```bash
# 运行 scan 并查看收集到的元素
aat scan --url https://www.bing.com.cn

# 查看 scan_result.json
cat .aat/scan_result.json | jq '.elements[] | select(.source == "accessibility")'
```

### 验证 Snapshot Ref

```python
# 在 executor 运行时查看日志
# [Executor] Using snapshot ref: e5
# [Executor] Snapshot ref 'e5' resolved to (630, 170)
```

### 常见问题

**Q: Snapshot ref 找不到元素？**

**A:** 可能原因：
- 页面发生了导航（需要重新 scan）
- 元素被动态隐藏/删除
- Snapshot 时元素不存在

**解决**：Executor 会自动回退到 DOM/OCR，无需手动干预。

**Q: Accessibility 返回空元素？**

**A:** 可能原因：
- 页面没有 ARIA 标签
- 页面还在加载中（增加等待时间）
- 特殊技术栈（某些 Canvas 应用）

**解决**：SCAN 会自动回退到 DOM 查询。

## 性能影响

### SCAN 时间对比

| 阶段 | DOM 查询 | Accessibility + DOM |
|------|---------|---------------------|
| 简单页面 | ~2s | ~2.5s |
| 复杂页面 | ~4s | ~3s |
| 大型 SPA | ~6s | ~4s |

### 优化建议

1. **首次使用**：先用 DOM 查询验证
2. **生产环境**：优先 Accessibility（过滤更准确）
3. **CI/CD**：考虑超时设置（某些 A11y 树很慢）

## 最佳实践

1. **优先使用 snapshot_ref**：最可靠，自动过滤装饰性元素
2. **提供 role 信息**：增强匹配准确性（role="button"）
3. **重新 Scan**：页面变更后（导航、动态内容）
4. **保留 selector 作为回退**：确保向后兼容
5. **结合使用**：Accessibility（主要）+ DOM（回退）+ OCR（Canvas）

## 兼容性

### 向后兼容

✅ 现有场景继续运行（使用 selector/text）
✅ 现有 YAML 格式无需修改
✅ DOM/OCR 回退保障可靠性

### 渐进迁移

旧场景：
```yaml
- action: find_and_click
  target:
    selector: "#search_icon"
```

新场景（推荐）：
```yaml
- action: find_and_click
  target:
    snapshot_ref: "e5"
    role: "button"
```

两种格式都支持，优先使用新格式！
