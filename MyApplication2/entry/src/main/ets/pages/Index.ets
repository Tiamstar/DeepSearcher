import promptAction from '@ohos.promptAction'
import { ImagePreview, ImagePreviewConfig, ImagePreviewSwiper } from '@rv/image-preview'

@Entry @ComponentV2
struct Index {
  @Local imageList: string[] = [
    'https://example.com/image1.jpg',
    'https://example.com/image2.jpg',
    'https://example.com/image3.jpg'
  ]
  private config: ImagePreviewConfig = new ImagePreviewConfig()
    .setIndicatorCount(3)
    .setMaxScale(3)
    .setMinScale(0.5)
    .setDoubleClickDefaultScale(3)
    .setInitialIndex(1)
    .setOnScrollIndex((index: number) => {
    })
    .setOnClick((index: number) => {
    })
    .setOnLongPress((index: number) => {
    })

  @Builder imageChild(data: Index) {
    ForEach(data.imageList, (item: string) => {
      ImagePreview({
        config: new ImagePreviewConfig().setOnClick(() => {})
      }) {
        Image(item)
          .fitOriginalSize(true)
      }
    })
  }

  build() {
    Column() {
      Flex({ justifyContent: FlexAlign.SpaceBetween }) {
        Button('Text')
          .onClick(() => this.config.prevPage())

        Button('Text')
          .onClick(() => this.config.nextPage())

        Button('Text')
          .onClick(() => this.config.scrollToIndex(2))

        Button('Text')
          .onClick(() => {
            this.imageList.push('https://example.com/newimage.jpg')
            this.config.setIndicatorCount(this.imageList.length)
          })
      }
      .width('100%')
      .padding(10)

      Stack() {
        ImagePreviewSwiper({
          config: this.config,
          data: this,
          imagesBuilder: this.imageChild
        })
      }
      .width('100%')
      .height('80%')
    }
    .backgroundColor(Color.Pink)
    .width('100%')
    .height('100%')
  }
}