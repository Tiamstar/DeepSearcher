import { ImageAnimUtil } from '../common/CommonUtil'

/**
 * 日期：2025/6/7
 */
@ObservedV2
export class ImagePreviewState {
  public readonly animUtil: ImageAnimUtil
  @Trace public centerX: number = 0 // 缩放中心X
  @Trace public centerY: number = 0 // 缩放中心Y
  @Trace public offsetX: number = 0 // 偏移X
  @Trace public offsetY: number = 0 // 偏移Y
  @Trace public scale: number = 1 // 缩放比例
  @Trace public imageWidth: number = 0 // 图片宽度
  @Trace public imageHeight: number = 0 // 图片高度
  @Trace public previewWidth: number = 0 // 预览宽度
  @Trace public previewHeight: number = 0 // 预览高度
  public lastScale: number = 1 // 上一次缩放比例
  public lastOffsetX: number = 0 // 上一次偏移X
  public lastOffsetY: number = 0 // 上一次偏移Y
  public scrollOffset: number = 0 // 滚动偏移

  constructor(uiContext: UIContext) {
    this.animUtil = new ImageAnimUtil(uiContext)
  }


  /**
   * 缩放动画
   */
  public set scaleAnim(scale: number) {
    this.animUtil.playScale(this.scale, scale, (progress: number) => {
      this.scale = progress
      this.lastScale = progress
    })
  }

  /**
   * 偏移动画
   */
  public set offsetXAnim(offsetX: number) {
    this.animUtil.playOffsetX(this.offsetX, offsetX, (progress: number) => {
      this.offsetX = progress
      this.lastOffsetX = progress
    })
  }

  /**
   * 偏移动画
   */
  public set offsetYAnim(offsetY: number) {
    this.animUtil.playOffsetY(this.offsetY, offsetY, (progress: number) => {
      this.offsetY = progress
      this.lastOffsetY = progress
    })
  }


  /**
   * 在左边界
   */
  public get isOnLeftBoundary(): boolean {
    return this.offsetX >= this.maxOffsetX
  }

  /**
   * 在右边界
   */
  public get isOnRightBoundary(): boolean {
    return this.offsetX <= this.minOffsetX
  }

  // 左边界，最大 X 位移值
  @Computed
  public get maxOffsetX(): number {
    return Math.abs(Math.min((1 - this.scale) * this.previewWidth / 2, 0))
  }

  // 右边界，最大 Y 位移值
  @Computed
  public get minOffsetX(): number {
    return -Math.abs(Math.max(this.previewWidth * (this.scale - 1) / 2, 0));
  }

  // 顶部边界，最大 Y 位移值
  @Computed
  public get maxOffsetY(): number {
    return Math.abs(Math.min((this.previewHeight -
      this.scale * this.imageHeight * this.previewWidth / this.imageWidth) / 2, 0));
  }

  // 底部边界，最大 Y 位移值
  @Computed
  public get minOffsetY(): number {
    return -Math.abs(Math.max((this.scale * this.imageHeight * this.previewWidth / this.imageWidth -
    this.previewHeight) / 2, 0));
  }

}

