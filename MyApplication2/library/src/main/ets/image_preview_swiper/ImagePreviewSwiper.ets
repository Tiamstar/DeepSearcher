import { FULL_PERCENT, IMAGE_PREVIEW_SWIPER_CONTROLLER as IMAGE_PREVIEW_SWIPER_CONFIG } from '../common/CommonUtil'
import { ImagePreviewConfig } from '../common/ExportModel'
import { ImagePreviewSwiperConfig } from './ImagePreviewSwiperConfig'

/**
 * 日期：2025/6/7
 */
@ComponentV2
export struct ImagePreviewSwiper {
  private readonly listScroller: ListScroller = new ListScroller()
  @BuilderParam imagesBuilder: Function
  @Param data: Object | undefined = undefined
  @Param config: ImagePreviewConfig = new ImagePreviewConfig()
  @Provider(IMAGE_PREVIEW_SWIPER_CONFIG) private readonly swiperConfig: ImagePreviewSwiperConfig =
    new ImagePreviewSwiperConfig(this.listScroller, this.config)

  @Monitor("data")
  private onDataChange() {
    return
  }

  build() {
    if (this.imagesBuilder) {
      Stack({ alignContent: Alignment.Bottom }) {
        List({ scroller: this.swiperConfig.listScroller, initialIndex: this.config.initialIndex }) {
          this.imagesBuilder(this.data)
        }
        .cachedCount(this.config.cachedCount)
        .backgroundColor(this.config.backgroundColor)
        .friction(999)
        .scrollBar(BarState.Off)
        .edgeEffect(EdgeEffect.None)
        .scrollSnapAlign(ScrollSnapAlign.START)
        .listDirection(Axis.Horizontal)
        .enableScrollInteraction(false)
        .width(FULL_PERCENT)
        .height(FULL_PERCENT)
        .onScrollIndex((start: number, end: number, center: number) => {
          this.swiperConfig.isInScroll = start !== end
          this.config.onScrollIndex?.(start, end, center)
          this.swiperConfig.indicatorController.changeIndex(center, true)
          if (start === end) {
            this.swiperConfig.currentIndex = center
          }
        })

        if (this.config.showIndicator) {
          IndicatorComponent(this.swiperConfig.indicatorController)
            .enabled(false)
            .margin(16)
            .initialIndex(this.config?.initialIndex)
            .style(this.config?.indicatorStyle)
            .count(this.config?.indicatorCount)
        }
      }
    }
  }
}