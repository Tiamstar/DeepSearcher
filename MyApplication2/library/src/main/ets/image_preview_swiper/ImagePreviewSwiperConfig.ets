import { ImagePreviewConfig } from '../common/ExportModel'

/**
 * 日期：2025/6/18
 */
@ObservedV2
export class ImagePreviewSwiperConfig {
  public readonly config: ImagePreviewConfig
  public readonly listScroller: ListScroller | undefined
  public readonly indicatorController: IndicatorComponentController = new IndicatorComponentController()
  public currentIndex: number = -1
  @Trace public isInScroll: boolean = false

  constructor(scroll: ListScroller | undefined, config: ImagePreviewConfig | undefined) {
    this.currentIndex = config?.initialIndex ?? -1
    this.listScroller = scroll
    this.config = config ?? new ImagePreviewConfig()
    if (config) {
      config.listScroller = scroll
    }
  }
}