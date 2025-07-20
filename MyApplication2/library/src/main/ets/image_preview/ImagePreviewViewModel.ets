import { ImagePreviewConfig } from '../common/ExportModel';
import { ImagePreviewSwiperConfig } from '../image_preview_swiper/ImagePreviewSwiperConfig';
import { ImagePreviewState } from './ImagePreviewState';

/**
 * 日期：2025/6/7
 */
export class ImagePreviewViewModel {
  private readonly state: ImagePreviewState
  private readonly config: ImagePreviewConfig
  private readonly swiperConfig: ImagePreviewSwiperConfig
  private readonly uiContext: UIContext

  constructor(context: UIContext, state: ImagePreviewState, swiperConfig: ImagePreviewSwiperConfig) {
    this.uiContext = context;
    this.state = state;
    this.config = swiperConfig.config;
    this.swiperConfig = swiperConfig;
  }

  public onDoubleClick = (event: GestureEvent) => {
    this.onGestureStart()
    const state = this.state;
    const finger = event.fingerList[event.fingerList.length - 1];
    this.state.centerX = 1 - this.evaluateCenterX(finger.localX);
    this.state.centerY = 1 - this.evaluateCenterY(finger.localY);
    if (state.scale != 1) {
      this.reset(true)
    }
    else {
      this.onScale(this.config.doubleClickDefaultScale, state.offsetX, state.offsetY, true)
    }
  }
  public onPinchStart = (event: GestureEvent) => {
    this.onGestureStart()
    this.state.centerX = 1 - this.evaluateCenterX(event.pinchCenterX);
    this.state.centerY = 1 - this.evaluateCenterY(event.pinchCenterY);
  }
  public onPinchUpdate = (event: GestureEvent) => {
    if (this.swiperConfig.isInScroll) {
      return
    }
    this.onScale(event.scale, event.offsetX, event.offsetY);
  }
  public onPinchEnd = (event: GestureEvent) => {
    this.optimizeScale(true)
  }
  public onPanStart = (event: GestureEvent) => {
    this.onGestureStart()
  }
  public onPanUpdate = (event: GestureEvent) => {
    const state = this.state;
    if ((state.isOnLeftBoundary && event.offsetX > 0) || (state.isOnRightBoundary && event.offsetX < 0)
      || this.swiperConfig.isInScroll) {
      this.swiperConfig.listScroller?.scrollBy(state.scrollOffset - event.offsetX, 0)
      state.scrollOffset = event.offsetX
      return
    }
    this.onScale(event.scale, event.offsetX, event.offsetY);
  }
  public onPanEnd = (event: GestureEvent) => {
    const state = this.state;
    if ((state.isOnLeftBoundary && event.offsetX > 0) || (state.isOnRightBoundary && event.offsetX < 0)) {
      this.swiperConfig.listScroller?.fling(event.velocityX)
      return
    }
    state.offsetXAnim = this.getLegalOffsetX(state.offsetX + event.velocityX / state.scale);
    state.offsetYAnim = this.getLegalOffsetY(state.offsetY + event.velocityY / state.scale);
  }
  public onLongPress = (event: GestureEvent) => {
    this.config.onLongPress?.(this.swiperConfig.currentIndex, event)
  }
  public onClick = (event: GestureEvent) => {
    this.config.onClick?.(this.swiperConfig.currentIndex, event)
  }

  /**
   * 计算当前图片的X轴偏移量、Y轴偏移量以及当前图片的缩放比例值
   * @param scale
   * @param offX
   * @param offY
   */
  private onScale(scale: number, offX: number, offY: number, needAnim = false) {
    const state = this.state;
    const option = this.config;
    const maxScale = option.maxScale;
    const tmpScale = Math.min(state.lastScale * scale, maxScale);
    const tmpOffsetX = this.getLegalOffsetX((state.lastOffsetX + offX) +
      (0.5 - state.centerX) * state.imageWidth * (1 - scale) * state.lastScale)
    const tmpOffsetY = this.getLegalOffsetY((state.lastOffsetY + offY)
      + (0.5 - state.centerY) * state.imageHeight * (1 - scale) * state.lastScale)
    if (needAnim) {
      state.scaleAnim = tmpScale
      if (state.scale <= maxScale) {
        state.offsetYAnim = tmpOffsetY
        state.offsetXAnim = tmpOffsetX
      }
    }
    else {
      state.scale = tmpScale
      if (state.scale <= maxScale) {
        state.offsetY = tmpOffsetY
        state.offsetX = tmpOffsetX
      }
    }
  }

  /**
   * 手势开始事件
   */
  private onGestureStart() {
    const state = this.state;
    state.animUtil.stop()
    state.lastScale = state.scale;
    state.lastOffsetX = state.offsetX;
    state.lastOffsetY = state.offsetY;
    state.scrollOffset = 0
  }

  /**
   * 计算当前缩放中心相对于图片的百分比位置
   */
  private evaluateCenterX(fingerX: number): number {
    const state = this.state;
    let imgDisplayWidth = state.imageWidth * state.scale;
    let imgX = (state.previewWidth - imgDisplayWidth) / 2 + state.lastOffsetX;
    return Math.max((fingerX - imgX) / imgDisplayWidth, 0);
  }

  /**
   * 计算当前缩放中心相对于图片的百分比位置
   */
  private evaluateCenterY(fingerY: number): number {
    const state = this.state;
    let imgDisplayHeight = state.imageHeight * state.scale;
    let imgY = (state.previewHeight - imgDisplayHeight) / 2 + state.lastOffsetY;
    return Math.max((fingerY - imgY) / imgDisplayHeight, 0);
  }

  /**
   * 获取合法位移X
   */
  private getLegalOffsetX(offsetX: number): number {
    const state = this.state;
    return Math.max(Math.min(offsetX, state.maxOffsetX), state.minOffsetX);
  }

  /**
   * 获取合法位移Y
   */
  private getLegalOffsetY(offsetY: number): number {
    const state = this.state;
    return Math.max(Math.min(offsetY, state.maxOffsetY), state.minOffsetY);
  }

  /**
   * 优化缩放
   */
  private optimizeScale(needAnim: boolean = false): void {
    const state = this.state;
    const option = this.config;
    const tmp = Math.min(Math.max(state.scale, option.minScale), option.maxScale);
    this.onScale(tmp / state.lastScale, state.offsetX, state.offsetY, needAnim)
  }

  /**
   * 重置
   */
  public reset(needAnim: boolean = false): void {
    const state = this.state;
    if (needAnim) {
      state.scaleAnim = 1;
    }
    else {
      state.scale = 1;
    }
    state.lastScale = 1;
    state.centerX = 0.5;
    state.centerY = 0.5;
    this.offsetReset(needAnim)
  }

  /**
   * 偏移重置
   */
  private offsetReset(needAnim: boolean = false): void {
    const state = this.state;
    if (needAnim) {
      state.offsetXAnim = 0;
      state.offsetYAnim = 0;
    }
    else {
      state.offsetX = 0;
      state.offsetY = 0;
    }
    state.lastOffsetX = 0;
    state.lastOffsetY = 0;
  }
}


