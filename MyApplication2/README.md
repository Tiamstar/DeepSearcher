# 你的主要任务是根据下面描述生成这个项目的主页面代码，主页面代码的自然语言描述如下：

下面是对提供的 ArkTS 代码的自然语言描述，重点突出关键结构、配置项和交互逻辑，确保可据此准确生成代码：

---

### 组件结构
1. **入口组件**  
   - 名为 `Index` 的 `@Entry` 组件
   - 使用 `@ComponentV2` 装饰器
   - 粉色背景（`Color.Pink`），占满全屏

2. **图片数据**  
   - 私有变量 `imageList`：存储 3 个相同网络图片 URL 的数组
   - 使用 `@Local` 装饰器管理状态

---

### 图片预览配置 (`ImagePreviewConfig`)
通过链式调用配置：
- `setIndicatorCount()`：指示器数量 = 图片数组长度
- `setMaxScale(3)`：最大缩放比例 3 倍
- `setMinScale(0.5)`：最小缩放比例 0.5 倍
- `setDoubleClickDefaultScale(3)`：双击默认放大到 3 倍
- `setInitialIndex(1)`：初始显示第二张图片（索引 1）
- **交互回调**：
  - `setOnScrollIndex()`：滚动时显示 Toast 提示当前中心图片索引
  - `setOnClick()`：点击图片时显示 Toast（提示父组件点击 + 索引）
  - `setOnLongPress()`：长按图片时显示 Toast（提示长按事件 + 索引）

---

### 构建函数 (`build()`)
#### 1. 顶部按钮栏 (`Flex` 布局)
- **上一页按钮**：点击触发 `config.prevPage()`
- **下一页按钮**：点击触发 `config.nextPage()`
- **跳转按钮**：点击滚动到第 3 张图片（索引 2）
- **添加图片按钮**：
  - 向 `imageList` 追加新图片 URL
  - 更新指示器数量：`config.setIndicatorCount(imageList.length)`

#### 2. 图片预览区域 (`Stack`)
- 使用 `ImagePreviewSwiper` 组件：
  - `config`：传入配置对象
  - `data`：传递当前组件上下文（`this`）
  - `imagesBuilder`：绑定自定义构建器 `imageChild`

---

### 自定义图片构建器 (`@Builder imageChild`)
- **参数**：接收父组件数据 (`data: Index`)
- **遍历图片数组**：使用 `ForEach` 生成每张图片
- **每张图片结构**：
  ```typescript
  ImagePreview({
    config: new ImagePreviewConfig().setOnClick(() => {
      // 子组件点击事件（实际因嵌套在 Swiper 内不会触发）
    })
  }) {
    Image(item)  // 加载网络图片
      .fitOriginalSize(true)  // 保持原始尺寸
  }
  ```
- **关键限制**：
  - 当 `ImagePreview` 作为 `ImagePreviewSwiper` 子组件时，其配置的 `config` 会失效
  - 必须通过参数 `data` 访问父组件数据（避免 `this` 指向问题）

---

### 核心交互逻辑
1. **翻页控制**：通过按钮调用 `config.prevPage()`/`nextPage()`
2. **动态添加图片**：修改 `imageList` 后需手动更新指示器数量
3. **事件反馈**：
   - 滚动/点击/长按均触发 Toast 消息
   - 子组件的点击事件被父组件覆盖（实际不生效）

---

### 注意事项（代码生成关键点）
1. **组件导入**：  
   ```typescript
   import { ImagePreview, ImagePreviewConfig, ImagePreviewSwiper } from '@rv/image-preview'
   ```
2. **数据传递**：  
   `ImagePreviewSwiper` 的 `data` 属性传递 `this`，使构建器能访问 `imageList`
3. **配置失效规则**：
   - 嵌套在 `ImagePreviewSwiper` 中的 `ImagePreview` 的配置会失效
   - 滚动相关配置仅在 `ImagePreviewSwiper` 有效
4. **构建器签名**：  
   `@Builder imageChild(data: Index): void` 必须严格匹配参数类型

---

