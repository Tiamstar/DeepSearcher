# ImagePreview

## 简介

image-preview 提供图片预览组件，可以像使用 Swiper 一样方便的预览图片等不同组件，支持缩放和平移，提供一些自定义属性和事件监听。

## 下载安装

ohpm install @rv/image-preview

# 权限

无需权限，若使用网络资源图片，需要互联网访问权限。

## 子组件

仅支持 ImagePreview 组件，ImagePreviewSwiper 需传入 @Builder 修饰的自定义构建函数。因尾随闭包上下文丢失，所以暂时无法使用尾随闭包方式传入子组件

支持通过渲染控制类型（if/else、ForEach、Repeat）动态生成子组件，更推荐使用 Repeat 以优化性能。

> ### 说明
> 因使用的 V2 状态管理，暂不支持使用 LazyForEach 进行懒加载，有需求的同学可以自行下载源码改成 V1 形式。

## 接口

### ImagePreviewSwiper

ImagePreviewSwiper({imagesBuilder: CustomBuilder, config: ImagePreviewConfig})

作为 ImagePreview 的父组件，使 ImagePreview 支持翻页

| 参数            | 说明     | 类型                 | 默认值 |
|---------------|--------|--------------------|-----|
| imagesBuilder | 构建图片组件 | CustomBuilder      | -   |
| config        | 配置     | ImagePreviewConfig | -   |

### ImagePreview

ImagePreview({imageBuilder: CustomBuilder, config: ImagePreviewConfig})

预览一张图片

| 参数           | 说明     | 类型                 | 默认值 |
|--------------|--------|--------------------|-----|
| imageBuilder | 构建图片组件 | CustomBuilder      | -   |
| config       | 配置     | ImagePreviewConfig | -   |

## ImagePreviewConfig 说明

### 属性

| 参数                       | 说明          | 类型                                                    | 默认值  |
|--------------------------|-------------|-------------------------------------------------------|------|
| _doubleClickDefaultScale | 双击缩放图片的默认比例 | number                                                | 2    |
| _maxScale                | 最大缩放比例      | number                                                | 4    |
| _minScale                | 最小缩放比例      | number                                                | 1    |
| _onLongPress             | 长按图片的回调     | (index:number,event: GestureEvent) => void            | -    |
| _onClick                 | 点击图片的回调     | (index:number,event: GestureEvent) => void            | -    |
| _indicatorStyle          | 指示器的样式      | DotIndicator \| DigitIndicator                        | -    |
| _indicatorCount          | 指示器的数量      | number                                                | -    |
| _initialIndex            | 初始索引        | number                                                | 0    |
| _onScrollIndex           | 滚动到指定索引的回调  | (start: number, end: number, center: number)  => void | -    |
| _backgroundColor         | 背景色         | ResourceColor                                         | -    |
| _showIndicator           | 是否显示指示器     | boolean                                               | true |
| _cachedCount             | 缓存数量        | number                                                | -    |

## 方法

### nextPage

nextPage(animation: boolean = true)

跳转到下一页，不推荐快速连续调用，有需求请使用 scrollToIndex。

参数：

- animation: boolean 是否需要动画，默认为 true

### prevPage

prevPage(animation: boolean = true)

跳转到上一页，不推荐快速连续调用，有需求请使用 scrollToIndex。

参数：

- animation: boolean 是否需要动画，默认为 true

### scrollToIndex

scrollToIndex(index: number, animation: boolean = true)

跳转到指定索引的页。

参数：

- index: number 指定索引
- animation: boolean 是否需要动画，默认为 true

# 快速使用

``` typescript

import { ImagePreview, ImagePreviewConfig, ImagePreviewSwiper } from '@rv/image-preview';

@Entry
@Component
struct Index {
  // 配置属性
  private config = new ImagePreviewConfig()
    .setIndicatorCount(5)
    .setMaxScale(3)
    .setMinScale(0.5)
    .setDoubleClickDefaultScale(3)
    .setInitialIndex(1)
    .setOnScrollIndex((start, end, center) => {
      this.getUIContext().getPromptAction().showToast({ message: "当前图片索引：" + center })
    })
    .setOnClick(() => {
      this.getUIContext().getPromptAction().showToast({ message: "父组件点击了图片" })
    })
    .setOnLongPress(() => {
      this.getUIContext().getPromptAction().showToast({ message: "长按事件" })
    })

  build() {
    Column() {
      Flex() {
        Button("上一页").onClick(() => {
          this.config.prevPage()
        })
        Button("下一页").onClick(() => {
          this.config.nextPage()
        })
      }

      Stack() {
        // 传入自定义 Builder，因尾随闭包形式与该页面共享上下文，
        // 导致内部无法使用 @Provider，所以暂不支持尾随闭包形式，
        ImagePreviewSwiper({
          imagesBuilder: this.imagesBuilder,
          config: this.config
        })
      }.layoutWeight(1)
    }
    .backgroundColor(Color.Pink)
    .height('100%')
    .width('100%')
  }

  /**
   * 自定义 Builder 无需使用容器包裹内部组件，类似 Swiper 的写法，
   * 可使用 Repeat 和 Foreach，因使用的是 V2 状态管理，不支持 LazyForeach
   */
  @Builder
  imagesBuilder() {
    // 使用 ImagePreview 组件包裹需要预览的图片（不只是图片，所有组件理论上都可行），组件比例需要自行调节
    ImagePreview() {
      Image("https://tc.alcy.cc/i/2024/04/21/6624167024283.webp").fitOriginalSize(true)
    }

    // 可单独使用 ImagePreview 预览一张图片，ImagePreviewConfig 中有关滚动的配置失效，
    // 若 ImagePreview 作为 ImagePreviewSwiper 子组件，配置的 config 完全失效
    ImagePreview({
      config: new ImagePreviewConfig() 
        .setOnClick(() => {
          // 由于该组件作为 ImagePreviewSwiper 的子组件，config 失效，点击事件不会触发
          this.getUIContext().getPromptAction().showToast({ message: "点击了单独图片" })
        })
    }) {
      Image("https://tc.alcy.cc/i/2024/04/21/6624167024283.webp").fitOriginalSize(true)
    }

    ImagePreview() {
      Image("https://tc.alcy.cc/i/2024/04/21/6624167024283.webp").fitOriginalSize(true)
    }

    ImagePreview() {
      Image("https://tc.alcy.cc/i/2024/04/21/6624167024283.webp").fitOriginalSize(true)
    }

    ImagePreview() {
      Image("https://tc.alcy.cc/i/2024/04/21/6624167024283.webp").fitOriginalSize(true)
    }
  }
}

```